from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import ValidationError
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.application.attachment_import.commands.import_documents import (
    AttachmentImportCommands,
)
from backend.application.attachment_import.errors import (
    AttachmentImportError,
    ImportConflict,
    ImportGone,
    ImportLimitExceeded,
    ImportNotFound,
    ImportStorageError,
    InvalidAttachment,
    UnsupportedAttachment,
)
from backend.application.attachment_import.queries.import_history import (
    ImportHistoryQueries,
)
from backend.application.file_upload.commands.models import UploadSpec
from backend.application.file_upload.errors import (
    FileUploadError,
    InvalidUpload,
    UploadConflict,
    UploadGone,
    UploadLimitExceeded,
    UploadStorageError,
)
from backend.config.upload_settings import CHUNK_BYTES

from .attachment_import_models import (
    AttachmentImportResponse,
    ImportConflictResponse,
    ImportErrorResponse,
    ImportListResponse,
    UploadRequest,
    UploadResponse,
)
from .dependencies import get_import_queries, get_import_service

BODY_LIMIT = 11 * 1024 * 1024
FILE_LIMIT = 10 * 1024 * 1024

router = APIRouter(prefix="/api/attachment-imports", tags=["attachment-imports"])

ImportService = Annotated[AttachmentImportCommands, Depends(get_import_service)]
ImportQueries = Annotated[ImportHistoryQueries, Depends(get_import_queries)]


def error(
    status: int, code: str, message: str, *, phase: str = "validation"
) -> HTTPException:
    return HTTPException(
        status, detail={"code": code, "message": message, "phase": phase}
    )


def import_error(exc: AttachmentImportError | FileUploadError) -> HTTPException:
    statuses = {
        ImportConflict: 409,
        UploadConflict: 409,
        UploadGone: 410,
        UploadLimitExceeded: 413,
        UploadStorageError: 500,
        InvalidUpload: 422,
        ImportLimitExceeded: 413,
        ImportNotFound: 404,
        ImportGone: 410,
        ImportStorageError: 500,
        InvalidAttachment: 422,
        UnsupportedAttachment: 415,
    }
    result = error(statuses[type(exc)], exc.code, exc.message, phase=exc.phase)
    if isinstance(exc, (ImportConflict, UploadConflict)):
        detail = {
            "code": exc.code,
            "message": exc.message,
            "phase": exc.phase,
            "conflicts": [
                {"yj_code": code, "version_ids": list(versions)}
                for code, versions in (
                    exc.conflicts if isinstance(exc, ImportConflict) else ()
                )
            ],
        }
        result = HTTPException(statuses[type(exc)], detail=detail)
    return result


async def bounded_body(request: Request, limit: int) -> bytes:
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > limit:
            raise error(413, "request_too_large", "受信データが上限を超えています。")
        body.extend(chunk)
    return bytes(body)


@router.post(
    "/uploads",
    response_model=UploadResponse,
    status_code=201,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {"schema": UploadRequest.model_json_schema()},
            },
        }
    },
)
async def start_upload(request: Request, service: ImportService) -> UploadResponse:
    raw = await bounded_body(request, 4096)
    try:
        data = UploadRequest.model_validate_json(raw)
        spec = UploadSpec(data.filename, data.byte_size, data.source_sha256)
        upload_id = await service.start_upload(spec)
    except ValidationError, ValueError:
        raise error(422, "invalid_upload", "XMLのファイル情報が不正です。") from None
    except (AttachmentImportError, FileUploadError) as exc:
        raise import_error(exc) from None
    return UploadResponse(upload_id=upload_id)


@router.post(
    "/uploads/{upload_id}/parts/{index}",
    status_code=204,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"}
                },
            },
        }
    },
)
async def upload_part(
    upload_id: str, index: int, request: Request, service: ImportService
) -> Response:
    content = await bounded_body(request, CHUNK_BYTES)
    try:
        await service.upload_part(upload_id, index, content)
    except (AttachmentImportError, FileUploadError) as exc:
        raise import_error(exc) from None
    return Response(status_code=204)


@router.post(
    "/uploads/{upload_id}/complete",
    response_model=AttachmentImportResponse,
    status_code=201,
)
async def finish_upload(
    upload_id: str, response: Response, service: ImportService
) -> AttachmentImportResponse:
    try:
        result = await service.finish_upload(upload_id)
    except (AttachmentImportError, FileUploadError) as exc:
        raise import_error(exc) from None
    response.status_code = 200 if result.reused else 201
    response.headers["Location"] = (
        f"/api/attachment-imports/{quote(result.document_id, safe='')}/{result.source_sha256}"
    )
    return AttachmentImportResponse.from_result(result)


@router.post(
    "",
    response_model=AttachmentImportResponse,
    status_code=201,
    responses={
        200: {"model": AttachmentImportResponse},
        409: {"model": ImportConflictResponse},
        **{
            status: {"model": ImportErrorResponse}
            for status in (400, 413, 415, 422, 500)
        },
    },
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["file"],
                        "properties": {"file": {"type": "string", "format": "binary"}},
                    }
                }
            },
        }
    },
)
async def import_attachment(
    request: Request, response: Response, service: ImportService
) -> AttachmentImportResponse:
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > BODY_LIMIT:
            raise error(413, "request_too_large", "受信データが上限を超えています。")
        body.extend(chunk)
    request._body = bytes(body)
    try:
        async with request.form(
            max_files=2, max_fields=1, max_part_size=BODY_LIMIT
        ) as form:
            items = form.multi_items()
            if (
                len(items) != 1
                or items[0][0] != "file"
                or not isinstance(items[0][1], UploadFile)
            ):
                raise error(400, "file_required", "XMLファイルを1つ選択してください。")
            file = items[0][1]
            source = await file.read(FILE_LIMIT + 1)
            if not source:
                raise error(400, "empty_file", "空のファイルは取り込めません。")
            if len(source) > FILE_LIMIT:
                raise error(
                    413, "source_too_large", "XMLファイルが上限を超えています。"
                )
            result = await service.import_document(
                source, original_filename=file.filename or "source.xml"
            )
    except (AttachmentImportError, FileUploadError) as exc:
        raise import_error(exc) from None
    except StarletteHTTPException as exc:
        if isinstance(exc.detail, dict):
            raise
        raise error(
            400, "invalid_multipart", "XMLファイルを1つ選択してください。"
        ) from None
    response.status_code = 200 if result.reused else 201
    response.headers["Location"] = (
        f"/api/attachment-imports/{quote(result.document_id, safe='')}/{result.source_sha256}"
    )
    return AttachmentImportResponse.from_result(result)


@router.get("", response_model=ImportListResponse)
async def list_attachments(
    service: ImportQueries,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ImportListResponse:
    try:
        page = await service.list_imports(limit=limit, offset=offset)
    except (AttachmentImportError, FileUploadError) as exc:
        raise import_error(exc) from None
    return ImportListResponse.from_page(page, limit=limit, offset=offset)


@router.get(
    "/{document_id:path}/{source_sha256}",
    response_model=AttachmentImportResponse,
    responses={
        status: {"model": ImportErrorResponse} for status in (404, 409, 410, 500)
    },
)
async def read_attachment(
    document_id: str, source_sha256: str, service: ImportQueries
) -> AttachmentImportResponse:
    try:
        result = await service.read_result(document_id, source_sha256)
    except (AttachmentImportError, FileUploadError) as exc:
        raise import_error(exc) from None
    except ValueError:
        raise error(404, "not_found", "保存済みの取り込みが見つかりません。") from None
    return AttachmentImportResponse.from_result(result)
