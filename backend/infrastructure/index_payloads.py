"""純粋な構造化JSONから索引値と検索用文字列・登録生成物を組み立てる。"""

import html
import json
from typing import Any

from backend.application.medicine.product_models import RegisteredMedicine
from backend.domain.attachment.value_objects import MedicineDocumentReference
from backend.domain.medicine.entities import MedicineProduct

from ..application.attachment_import.import_models import (
    ImportedProduct,
    ImportedRevision,
    ImportResult,
    ImportWarning,
)
from ..application.indexing.index_models import IndexDocument, IndexUnit
from ..domain.attachment.entities import AttachmentDocument
from ..domain.attachment.identifiers import DocumentId
from ..domain.attachment.primitives import PmdaUrl
from ..domain.attachment.value_objects import AttachmentProductRevision
from ..domain.foundation.json_types import JsonValue
from ..domain.medicine.identifiers import YjCode
from ..domain.retrieval.entities import SearchUnit
from ..domain.retrieval.value_objects import (
    SearchContentBlock,
    SearchContentReference,
    SearchParagraph,
    SearchTableBlock,
)
from ..domain.shared.services import normalize_search_text

MAX_ARTIFACT_BYTES = 32 * 1024 * 1024


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


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _reference(reference: SearchContentReference) -> dict[str, Any]:
    return {
        "kind": reference.label.value,
        "target_xml_id": reference.target_id.value if reference.target_id else None,
        **reference.metadata.to_dict(),
    }


def _block(block: SearchContentBlock) -> tuple[str, dict[str, Any]]:
    context = {
        "product_yj_codes": [code.value for code in block.context.product_codes],
        "labels": [label.value for label in block.context.labels],
    }
    references = [_reference(reference) for reference in block.references]
    if isinstance(block, SearchParagraph):
        rendered = "<p>" + html.escape(block.text.value).replace("\n", "<br>") + "</p>"
        payload = {"kind": "paragraph", "text": block.text.value}
    elif isinstance(block, SearchTableBlock):
        rows = []
        payload_rows = []
        for row in block.table.rows:
            rows.append(
                "<tr>"
                + "".join(
                    f'<td rowspan="{cell.rowspan}" colspan="{cell.colspan}">{html.escape(cell.text.value).replace(chr(10), "<br>")}</td>'
                    for cell in row
                )
                + "</tr>"
            )
            payload_rows.append(
                [
                    {
                        "text": cell.text.value,
                        "column": cell.column,
                        "rowspan": cell.rowspan,
                        "colspan": cell.colspan,
                        "product_yj_codes": [
                            code.value for code in cell.context.product_codes
                        ],
                        "references": [
                            _reference(reference) for reference in cell.references
                        ],
                    }
                    for cell in row
                ]
            )
        rendered = "<table><tbody>" + "".join(rows) + "</tbody></table>"
        payload = {
            "kind": "table",
            "columns": [column.value for column in block.table.columns],
            "rows": payload_rows,
        }
    else:
        rendered = "<p>" + html.escape(block.description.value) + "</p>"
        payload = {
            "kind": "figure",
            "reference": block.reference.value,
            "description": block.description.value,
        }
    labels = "".join(
        "<p><strong>〈" + html.escape(label.value) + "〉</strong></p>"
        for label in block.context.labels
    )
    return labels + rendered, {**payload, "context": context, "references": references}


def _render_registered_block(block: dict[str, JsonValue]) -> str:
    """Render both new and persisted registration blocks from their source fields."""
    kind = block["kind"]
    if kind == "table":
        columns = _strings(block.get("columns") or [])
        raw_rows = block.get("rows") or []
        if not isinstance(raw_rows, list):
            raise TypeError("Expected a JSON array of table rows")
        rows = [_objects(row) for row in raw_rows]
        header = ""
        # Generic XML tables may already carry their heading cells in the first row.
        first_row = [_string(cell["text"]) for cell in rows[0]] if rows else []
        if columns and columns != first_row:
            header = (
                "<thead><tr>"
                + "".join(
                    '<th scope="col">' + html.escape(column) + "</th>"
                    for column in columns
                )
                + "</tr></thead>"
            )
        body = []
        for row in rows:
            cells = []
            for cell in row:
                rowspan = cell["rowspan"]
                colspan = cell["colspan"]
                if type(rowspan) is not int or type(colspan) is not int:
                    raise TypeError("Expected integer table spans")
                value = html.escape(_string(cell["text"])).replace("\n", "<br>")
                cells.append(
                    f'<td rowspan="{rowspan}" colspan="{colspan}">{value}</td>'
                )
            body.append("<tr>" + "".join(cells) + "</tr>")
        rendered = "<table>" + header + "<tbody>" + "".join(body) + "</tbody></table>"
    elif kind in ("paragraph", "figure"):
        value = block["text"] if kind == "paragraph" else block["description"]
        escaped = html.escape(_string(value))
        rendered = (
            "<p>"
            + (escaped.replace("\n", "<br>") if kind == "paragraph" else escaped)
            + "</p>"
        )
    else:
        raise ValueError(f"Unknown registration block kind: {kind}")
    context = _object(block.get("context") or {})
    labels = "".join(
        "<p><strong>〈" + html.escape(label) + "〉</strong></p>"
        for label in _strings(context.get("labels") or [])
    )
    return labels + rendered


def registered_unit_text(unit: dict[str, JsonValue]) -> str:
    """Restore source column headings for existing v3 units without rewriting storage."""
    if unit.get("schema_version") == "medi-chat.pmda-sections.v3" and unit.get(
        "blocks"
    ):
        return "".join(
            _render_registered_block(block) for block in _objects(unit["blocks"])
        )
    return _string(unit.get("text") or "")


def encode_registered_units(
    document: AttachmentDocument, units: tuple[SearchUnit, ...]
) -> bytes:
    if document.source.sha256 is None:
        raise ValueError("registration source SHA required")
    rows = []
    for unit in units:
        blocks = [_block(block) for block in unit.blocks]
        rows.append(
            {
                "schema_version": "medi-chat.pmda-sections.v3",
                "document_key": document.document_id.value,
                "source_sha256": document.source.sha256.value,
                "version_id": f"{document.document_id.value}:{document.source.sha256.value}",
                "unit_id": unit.unit_id.value,
                "kind": unit.kind.value,
                "section": {
                    "code": unit.section_code.value,
                    "title": unit.section_title.value if unit.section_title else "",
                },
                "product_yj_codes": [code.value for code in unit.product_codes],
                "text": "".join(rendered for rendered, _ in blocks),
                "blocks": [payload for _, payload in blocks],
                "references": [
                    reference
                    for _, payload in blocks
                    for reference in payload["references"]
                ],
                "source": {"pmda_url": document.source.pmda_url.value},
                "revisions": [revision.to_dict() for revision in unit.revisions],
            }
        )
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode(
        "utf-8"
    )


def _object(value: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise TypeError("Expected a JSON object")
    return value


def _string(value: JsonValue) -> str:
    if not isinstance(value, str):
        raise TypeError("Expected a JSON string")
    return value


def _objects(value: JsonValue) -> list[dict[str, JsonValue]]:
    if not isinstance(value, list):
        raise TypeError("Expected a JSON array")
    return [_object(item) for item in value]


def _strings(value: JsonValue) -> list[str]:
    if not isinstance(value, list):
        raise TypeError("Expected a JSON array")
    return [_string(item) for item in value]


def build_index_unit(payload: dict[str, JsonValue], document_id: str) -> IndexUnit:
    columns = _object(payload.get("columns") or {})
    section = _object(payload.get("section") or {})
    searchable = [
        _string(payload.get("text", "")),
        " ".join(_strings(payload.get("context_labels") or [])),
        _string(section.get("title", "")),
        " ".join(str(value) for value in columns.values()),
    ]
    return IndexUnit(
        unit_id=_string(payload["unit_id"]),
        document_id=document_id,
        section_code=str(section.get("code", "")),
        kind=str(payload.get("kind", "")),
        payload=payload,
        query_text=normalize_search_text(" ".join(searchable)),
        drug_name=normalize_search_text(str(columns.get("drug_name", ""))),
    )


def build_index_document(
    payload: dict[str, JsonValue],
) -> tuple[IndexDocument, list[RegisteredMedicine]]:
    metadata = _object(payload.get("document") or {})
    source = _object(payload.get("source") or {})
    company = metadata.get("company_identifier")
    insert_no = metadata.get("package_insert_no")
    if not company or not insert_no:
        raise ValueError("Missing package insert number in document JSON")
    document_id = f"{company}_{insert_no}"
    medicines: list[RegisteredMedicine] = []
    revisions = _objects(metadata.get("revisions") or [])
    revision = revisions[-1] if revisions else {}
    for product in _objects(metadata.get("products") or []):
        yj_code = product.get("yj_code")
        medicines.append(
            RegisteredMedicine(
                medicine=MedicineProduct(
                    yj_code=YjCode(_string(yj_code)) if yj_code is not None else None,
                    brand_name=_string(product.get("brand_name") or ""),
                    generic_name=_string(metadata.get("generic_name") or ""),
                    english_name=_string(product.get("english_name") or ""),
                    hiragana_name=_string(product.get("hiragana_name") or ""),
                ),
                reference=MedicineDocumentReference(
                    document_id=DocumentId(document_id),
                    pmda_url=PmdaUrl(
                        _string(
                            source.get("pmda_url") or metadata.get("pmda_url") or ""
                        )
                    ),
                    revision=AttachmentProductRevision(revision),
                ),
            )
        )
    return IndexDocument(document_id, payload), medicines
