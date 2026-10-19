"""Handwritten registration input/DTO oracle, preserved from pre-PG tests."""

import hashlib


def source(body, codes=("111111111111",), *, doc="test", revised_at="2026-10"):
    from backend.tests.support.attachment_import_fixtures import xml_source

    value = xml_source(
        f"<Warnings><Detail><Lang>{body}</Lang></Detail></Warnings>"
    ).replace(
        b"<PackageInsertNo>test</PackageInsertNo>",
        f"<PackageInsertNo>{doc}</PackageInsertNo>".encode(),
    )
    value = value.replace(b"111111111111", codes[0].encode())
    if len(codes) > 1:
        value = value.replace(
            b"</ApprovalEtc>",
            f'<DetailBrandName id="B"><ApprovalBrandName><Lang>B薬</Lang></ApprovalBrandName><BrandCode><YJCode>{codes[1]}</YJCode></BrandCode></DetailBrandName></ApprovalEtc>'.encode(),
        )
    return value.replace(b"2026-10", revised_at.encode())


def expected(
    value,
    generation,
    sequence,
    codes,
    *,
    active=None,
    reused=False,
    status="registered",
    replaced=(),
    deleted=(),
    pending=(),
    artifacts_deleted=False,
    revised_at="2026-10",
):
    return {
        "document_id": "000001_test",
        "source_sha256": hashlib.sha256(value).hexdigest(),
        "status": status,
        "reused": reused,
        "validation_status": "pass",
        "section_count": 1,
        "search_unit_count": 1,
        "products": [
            {"yj_code": code, "brand_name": "製品A" if i == 0 else "B薬"}
            for i, code in enumerate(codes)
        ],
        "revisions": [
            {"source_label": "今回", "year_month": revised_at, "version": "1"}
        ],
        "warnings": [],
        "search_index_updated": bool(codes if active is None else active),
        "generation_id": generation,
        "registration_sequence": sequence,
        "active_yj_codes": list(codes if active is None else active),
        "replaced_yj_codes": list(replaced),
        "deleted_version_ids": list(deleted),
        "cleanup_pending": [
            {"version_id": version, "reason": reason} for version, reason in pending
        ],
        "artifacts_deleted": artifacts_deleted,
    }
