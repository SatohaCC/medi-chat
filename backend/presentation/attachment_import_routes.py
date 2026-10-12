from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..application.attachment_import.import_document import AttachmentImportService
from ..application.attachment_import.import_errors import (
    AttachmentImportError,
    ImportConflict,
    ImportGone,
    ImportLimitExceeded,
    ImportNotFound,
    ImportStorageError,
    InvalidAttachment,
    UnsupportedAttachment,
)
from ..domain.foundation.exceptions import DomainValidationError
from .attachment_import_models import (
    AttachmentImportResponse,
    ImportConflictResponse,
    ImportErrorResponse,
)

BODY_LIMIT = 11 * 1024 * 1024
FILE_LIMIT = 10 * 1024 * 1024

router = APIRouter(prefix="/api/attachment-imports", tags=["attachment-imports"])


def get_import_service(request: Request) -> AttachmentImportService:
    return request.app.state.attachment_import_service


ImportService = Annotated[AttachmentImportService, Depends(get_import_service)]


def error(
    status: int, code: str, message: str, *, phase: str = "validation"
) -> HTTPException:
    return HTTPException(
        status, detail={"code": code, "message": message, "phase": phase}
    )


def import_error(exc: AttachmentImportError) -> HTTPException:
    statuses = {
        ImportConflict: 409,
        ImportLimitExceeded: 413,
        ImportNotFound: 404,
        ImportGone: 410,
        ImportStorageError: 500,
        InvalidAttachment: 422,
        UnsupportedAttachment: 415,
    }
    result = error(statuses[type(exc)], exc.code, exc.message, phase=exc.phase)
    if isinstance(exc, ImportConflict):
        detail = {
            "code": exc.code,
            "message": exc.message,
            "phase": exc.phase,
            "conflicts": [
                {"yj_code": code, "version_ids": list(versions)}
                for code, versions in exc.conflicts
            ],
        }
        result = HTTPException(statuses[type(exc)], detail=detail)
    return result


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
    except AttachmentImportError as exc:
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


@router.get(
    "/{document_id:path}/{source_sha256}",
    response_model=AttachmentImportResponse,
    responses={
        status: {"model": ImportErrorResponse} for status in (404, 409, 410, 500)
    },
)
async def read_attachment(
    document_id: str, source_sha256: str, service: ImportService
) -> AttachmentImportResponse:
    try:
        result = await service.read_result(document_id, source_sha256)
    except AttachmentImportError as exc:
        raise import_error(exc) from None
    except DomainValidationError, ValueError:
        raise error(404, "not_found", "保存済みの取り込みが見つかりません。") from None
    return AttachmentImportResponse.from_result(result)
