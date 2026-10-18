"""Explicit, stopped-index backup checks; never called by application startup."""

import ctypes
import hashlib
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

from ..composition.index_verifier import verify_schema_readiness


def assert_stopped(target: Path) -> None:
    """Refuse an open Windows database/sidecar; callers must stop their own writers."""
    if sys.platform != "win32":
        raise RuntimeError("Stopped-file verification requires the Windows runbook")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_void_p,
    ]
    create.restype = ctypes.c_void_p
    close = kernel.CloseHandle
    close.argtypes = [ctypes.c_void_p]
    close.restype = ctypes.c_int
    for path in [target, Path(str(target) + "-wal"), Path(str(target) + "-shm")]:
        if not path.exists():
            continue
        handle = create(str(path.resolve()), 0x80000000, 0, None, 3, 0x80, None)
        if handle == ctypes.c_void_p(-1).value:
            raise RuntimeError(
                f"Database or sidecar is open; stop the owning writer: {path}"
            )
        close(handle)


def logical_snapshot(target: Path) -> dict:
    with closing(
        sqlite3.connect(f"{target.resolve().as_uri()}?mode=ro", uri=True)
    ) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        schema = connection.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
        ).fetchall()
        names = [row[1] for row in schema if row[0] == "table"]
        counts = {}
        rows = {}
        for name in names:
            quoted = '"' + name.replace('"', '""') + '"'
            values = connection.execute(f"SELECT * FROM {quoted}").fetchall()
            counts[name] = len(values)
            rows[name] = sorted(repr(row) for row in values)
        fingerprint = connection.execute(
            "SELECT value FROM index_meta WHERE key='source_fingerprint'"
        ).fetchone()[0]
        digest = hashlib.sha256(
            json.dumps([schema, rows], ensure_ascii=False).encode()
        ).hexdigest()
        return {
            "integrity": integrity,
            "tables": counts,
            "fingerprint": fingerprint,
            "logical_sha256": digest,
        }


def checked_backup(target: Path, backup: Path) -> dict:
    if not target.is_absolute() or not backup.is_absolute():
        raise RuntimeError("Both target and backup must be explicit absolute paths")
    if backup.exists():
        raise RuntimeError("Backup already exists; preserving it")
    assert_stopped(target)
    verify_schema_readiness(target)
    before = logical_snapshot(target)
    if before["integrity"] != "ok":
        raise RuntimeError("Target integrity check failed")
    with (
        closing(
            sqlite3.connect(f"{target.resolve().as_uri()}?mode=ro", uri=True)
        ) as source,
        closing(sqlite3.connect(backup)) as destination,
    ):
        source.backup(destination)
    after = logical_snapshot(backup)
    if after != before:
        raise RuntimeError("Backup logical verification failed")
    assert_stopped(target)
    if logical_snapshot(target) != before:
        raise RuntimeError("Target changed during backup; do not rebuild")
    return after


def verify_rebuild_preconditions(target: Path | None, backup: Path | None) -> None:
    if target is None or not target.is_absolute():
        raise RuntimeError("An explicit absolute target is required")
    if backup is None or not backup.is_absolute() or not backup.is_file():
        raise RuntimeError("A verified backup is required")
    assert_stopped(target)
    verify_schema_readiness(target)
    verify_schema_readiness(backup)
    original = logical_snapshot(target)
    if original["integrity"] != "ok" or logical_snapshot(backup) != original:
        raise RuntimeError("The backup does not match the stopped target")
