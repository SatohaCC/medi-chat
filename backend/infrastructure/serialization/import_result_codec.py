"""Codec for ImportResult serialization to and from JSON dictionary."""

from __future__ import annotations

from typing import Any

from backend.application.attachment_import.commands.models import (
    ImportedProduct,
    ImportedRevision,
    ImportResult,
    ImportWarning,
)


def result_dict(result: ImportResult) -> dict[str, Any]:
    return {
        "document_id": result.document_id,
        "source_sha256": result.source_sha256,
        "status": result.status,
        "reused": result.reused,
        "validation_status": result.validation_status,
        "section_count": result.section_count,
        "search_unit_count": result.search_unit_count,
        "products": [
            {"yj_code": product.yj_code, "brand_name": product.brand_name}
            for product in result.products
        ],
        "revisions": [
            {
                "source_label": revision.source_label,
                "year_month": revision.year_month,
                "version": revision.version,
            }
            for revision in result.revisions
        ],
        "warnings": [
            {"code": warning.code, "reference": warning.reference}
            for warning in result.warnings
        ],
        "transformer_version": result.transformer_version,
        "search_index_updated": result.search_index_updated,
    }


def result_from_dict(value: dict[str, Any]) -> ImportResult:
    return ImportResult(
        document_id=value["document_id"],
        source_sha256=value["source_sha256"],
        validation_status=value["validation_status"],
        section_count=value["section_count"],
        search_unit_count=value["search_unit_count"],
        products=tuple(
            ImportedProduct(product["yj_code"], product["brand_name"])
            for product in value["products"]
        ),
        revisions=tuple(
            ImportedRevision(
                revision["source_label"], revision["year_month"], revision["version"]
            )
            for revision in value["revisions"]
        ),
        warnings=tuple(
            ImportWarning(warning["code"], warning["reference"])
            for warning in value["warnings"]
        ),
        transformer_version=value["transformer_version"],
        reused=value["reused"],
        status=value["status"],
        search_index_updated=value["search_index_updated"],
    )
