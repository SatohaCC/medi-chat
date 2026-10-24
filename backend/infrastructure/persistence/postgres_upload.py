"""Short-lived bounded upload storage; no process-local or filesystem state."""

import hashlib
import re
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError

from backend.application.attachment_import.commands.models import UploadImportReceipt
from backend.application.file_upload.commands.models import UploadedSource, UploadSpec
from backend.application.file_upload.errors import (
    InvalidUpload,
    UploadConflict,
    UploadGone,
    UploadLimitExceeded,
    UploadStorageError,
)
from backend.config.upload_settings import CHUNK_BYTES

from .postgres_schema import upload_parts, uploads

MAX_UPLOADS = 16


class PostgresUploadStore:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        try:
            with self.engine.begin() as connection:
                yield connection
        except SQLAlchemyError:
            raise UploadStorageError(
                "upload_storage_failed", "XMLの一時保存に失敗しました。", phase="upload"
            ) from None

    def cleanup(self) -> None:
        with self._transaction() as connection:
            connection.execute(
                delete(uploads).where(uploads.c.expires_at <= func.now())
            )

    def create(self, spec: UploadSpec) -> str:
        with self._transaction() as connection:
            # Serialize only session admission, across all Function instances.
            connection.execute(
                text("SELECT pg_advisory_xact_lock(1835361385, 1970302063)")
            )
            connection.execute(
                delete(uploads).where(uploads.c.expires_at <= func.now())
            )
            # Completed sessions retain only receipt lookup metadata for retries.
            # Keep that cache bounded without preventing further manual imports.
            connection.execute(
                delete(uploads).where(
                    uploads.c.upload_id.in_(
                        select(uploads.c.upload_id)
                        .where(uploads.c.document_id.is_not(None))
                        .order_by(uploads.c.expires_at.desc())
                        .offset(64)
                    )
                )
            )
            if (
                connection.execute(
                    select(func.count())
                    .select_from(uploads)
                    .where(uploads.c.document_id.is_(None))
                ).scalar_one()
                >= MAX_UPLOADS
            ):
                raise UploadLimitExceeded(
                    "upload_capacity",
                    "取り込みが混み合っています。しばらく待って再送してください。",
                    phase="upload",
                )
            upload_id = secrets.token_hex(32)
            connection.execute(
                uploads.insert().values(
                    upload_id=upload_id,
                    filename=spec.filename,
                    byte_size=spec.byte_size,
                    source_sha256=spec.source_sha256,
                    expires_at=func.now() + timedelta(hours=1),
                )
            )
            return upload_id

    def _session(self, connection: Connection, upload_id: str):
        if not re.fullmatch(r"[0-9a-f]{64}", upload_id):
            raise UploadGone(
                "upload_expired",
                "取り込みを最初からやり直してください。",
                phase="upload",
            )
        row = (
            connection.execute(
                select(uploads)
                .where(
                    uploads.c.upload_id == upload_id,
                    uploads.c.expires_at > func.now(),
                )
                .with_for_update()
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise UploadGone(
                "upload_expired",
                "取り込みを最初からやり直してください。",
                phase="upload",
            )
        return row

    def put(self, upload_id: str, index: int, content: bytes) -> None:
        with self._transaction() as connection:
            row = self._session(connection, upload_id)
            spec = UploadSpec(row["filename"], row["byte_size"], row["source_sha256"])
            try:
                expected = spec.part_size(index, chunk_bytes=CHUNK_BYTES)
            except ValueError:
                raise InvalidUpload(
                    "invalid_upload_part",
                    "送信データの位置が不正です。",
                    phase="upload",
                ) from None
            if len(content) != expected:
                raise InvalidUpload(
                    "invalid_upload_part",
                    "送信データのサイズが一致しません。",
                    phase="upload",
                )
            if row["document_id"] is not None:
                raise UploadConflict(
                    "upload_complete", "このXMLは取り込み済みです。", phase="upload"
                )
            condition = (
                upload_parts.c.upload_id == upload_id,
                upload_parts.c.part_index == index,
            )
            existing = connection.execute(
                select(upload_parts.c.content).where(*condition)
            ).scalar_one_or_none()
            if existing is not None:
                if existing != content:
                    raise UploadConflict(
                        "upload_part_conflict",
                        "送信済みデータと一致しません。",
                        phase="upload",
                    )
                return
            connection.execute(
                upload_parts.insert().values(
                    upload_id=upload_id, part_index=index, content=content
                )
            )

    def read(self, upload_id: str) -> UploadedSource:
        with self._transaction() as connection:
            row = self._session(connection, upload_id)
            spec = UploadSpec(row["filename"], row["byte_size"], row["source_sha256"])
            if row["document_id"] is not None:
                raise UploadGone(
                    "upload_source_released", "登録済み原本は解放されています。"
                )
            parts = connection.execute(
                select(upload_parts.c.part_index, upload_parts.c.content)
                .where(
                    upload_parts.c.upload_id == upload_id,
                )
                .order_by(upload_parts.c.part_index)
            ).all()
            source = b"".join(part.content for part in parts)
            if len(source) != spec.byte_size:
                raise UploadConflict(
                    "upload_incomplete", "XMLの送信が完了していません。", phase="upload"
                )
            if hashlib.sha256(source).hexdigest() != spec.source_sha256:
                raise InvalidUpload(
                    "upload_digest_mismatch",
                    "XMLの整合性を確認できませんでした。再送してください。",
                    phase="upload",
                )
            return UploadedSource(spec, source)

    def discard(self, upload_id: str) -> None:
        with self._transaction() as connection:
            connection.execute(delete(uploads).where(uploads.c.upload_id == upload_id))


class PostgresUploadImportReceipts:
    def __init__(self, engine: Engine) -> None:
        self._store = PostgresUploadStore(engine)

    def find(self, upload_id: str) -> UploadImportReceipt | None:
        with self._store._transaction() as connection:
            row = self._store._session(connection, upload_id)
            if row["document_id"] is None:
                return None
            return UploadImportReceipt(row["document_id"], row["source_sha256"])

    def record(self, upload_id: str, document_id: str) -> None:
        with self._store._transaction() as connection:
            self._store._session(connection, upload_id)
            connection.execute(
                update(uploads)
                .where(uploads.c.upload_id == upload_id)
                .values(document_id=document_id)
            )
            connection.execute(
                delete(upload_parts).where(upload_parts.c.upload_id == upload_id)
            )
