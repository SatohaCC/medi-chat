"""純粋な構造化JSONから索引値と検索用文字列・登録生成物を組み立てる。"""

import html
import json
from typing import Any

from backend.application.medicine.product_models import RegisteredMedicine
from backend.domain.attachment.value_objects import MedicineDocumentReference
from backend.domain.medicine.entities import MedicineProduct
from backend.domain.medicine.primitives import (
    BrandName,
    EnglishName,
    GenericName,
    HiraganaName,
)
from backend.domain.medicine.value_objects import MedicineNames

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
from ..domain.retrieval.services import section_code_matches
from ..domain.retrieval.value_objects import (
    SearchContentBlock,
    SearchContentReference,
    SearchParagraph,
    SearchTableBlock,
)
from ..domain.shared.services import normalize_search_text

MAX_ARTIFACT_BYTES = 32 * 1024 * 1024
SEARCH_SCHEMA_VERSION = "medi-chat.pmda-sections.v4"
DOCUMENT_SCHEMA_VERSION = "medi-chat.pmda-prescription-xml.v2"


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
        "section": {
            "code": block.context.section_code.value,
            "title": block.context.section_title.value
            if block.context.section_title
            else "",
        }
        if block.context.section_code is not None
        else None,
    }
    references = [_reference(reference) for reference in block.references]
    if isinstance(block, SearchParagraph):
        rendered = "<p>" + html.escape(block.text.value).replace("\n", "<br>") + "</p>"
        payload = {
            "kind": "paragraph",
            "text": block.text.value,
            "is_heading": block.is_heading,
        }
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
    return rendered, {**payload, "context": context, "references": references}


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
        if columns:
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
        raw_value = block["text"] if kind == "paragraph" else block["description"]
        escaped = html.escape(_string(raw_value))
        rendered = (
            "<p>"
            + (escaped.replace("\n", "<br>") if kind == "paragraph" else escaped)
            + "</p>"
        )
        if kind == "paragraph" and block.get("is_heading") is True:
            rendered = "<p><strong>" + escaped.replace("\n", "<br>") + "</strong></p>"
    else:
        raise ValueError(f"Unknown registration block kind: {kind}")
    return rendered


def registered_unit_text(unit: dict[str, JsonValue]) -> str:
    """現在形式だけを読み取り、旧形式は再生成を要求する。"""
    if unit.get("schema_version") != SEARCH_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported search data format; regenerate from the original source"
        )
    if not isinstance(unit.get("blocks"), list):
        raise ValueError("Current search data requires structured blocks")
    return _string(unit["text"])


def _render_unit_blocks(unit: dict[str, JsonValue]) -> str:
    if unit.get("blocks"):
        rendered = []
        previous_code = None
        previous_products = None
        products = {
            _string(product["yj_code"]): _string(product["brand_name"])
            for product in _objects(unit.get("products") or [])
        }
        for block in _objects(unit["blocks"]):
            context = _object(block.get("context") or {})
            codes = tuple(
                dict.fromkeys(_strings(context.get("product_yj_codes") or []))
            )
            if len(products) > 1 and codes != previous_products:
                rendered.append(
                    '<p data-product-scope="true">対象製品: '
                    + " / ".join(
                        html.escape(products[code] + " [YJ: " + code + "]")
                        for code in codes
                    )
                    + "</p>"
                )
                previous_products = codes
            section = _object(context.get("section") or {})
            code = section.get("code")
            if code is not None and code != previous_code:
                # Standard numbered-section labels are separate from source Header nodes.
                rendered.append(
                    '<h3 data-section-code="'
                    + html.escape(_string(code), quote=True)
                    + '">'
                    + html.escape(_string(code))
                    + " "
                    + html.escape(_string(section.get("title") or ""))
                    + "</h3>"
                )
                previous_code = code
            rendered.append(_render_registered_block(block))
        return "".join(rendered)
    return ""


def unit_matches_sections(
    unit: dict[str, JsonValue], requested: tuple[str, ...]
) -> bool:
    """現在形式の大項目内に実在する番号だけを照合する。"""
    registered_unit_text(unit)
    codes = [_string(_object(unit.get("section") or {}).get("code") or "")]
    for block in _objects(unit.get("blocks") or []):
        context = _object(block.get("context") or {})
        section = _object(context.get("section") or {})
        if isinstance(section.get("code"), str):
            codes.append(_string(section["code"]))
    return not requested or any(
        section_code_matches(code, target) for code in codes for target in requested
    )


def encode_registered_units(
    document: AttachmentDocument,
    units: tuple[SearchUnit, ...],
    *,
    registered: bool = True,
) -> bytes:
    if document.source.sha256 is None:
        raise ValueError("registration source SHA required")
    rows = []
    for unit in units:
        blocks = [_block(block) for block in unit.blocks]
        payload = {
            "schema_version": SEARCH_SCHEMA_VERSION,
            "document_key": document.document_id.value,
            "source_sha256": document.source.sha256.value,
            "version_id": f"{document.document_id.value}:{document.source.sha256.value}"
            if registered
            else None,
            "unit_id": unit.unit_id.value,
            "kind": unit.kind.value,
            "section": {
                "code": unit.section_code.value,
                "title": unit.section_title.value if unit.section_title else "",
            },
            "product_yj_codes": [code.value for code in unit.product_codes],
            "products": [
                {
                    "yj_code": product.product_code.value,
                    "brand_name": product.brand_name.value,
                }
                for product in document.products
            ],
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
        payload["text"] = _render_unit_blocks(payload)  # type: ignore[arg-type]
        rows.append(payload)
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


def _optional_name_text(value: JsonValue) -> str | None:
    """任意名称の不在を識別し、実在する原表記は変更しない。"""
    if value is None:
        return None
    text = _string(value)
    return text if text.strip() else None


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
    revision = next(
        (revision for revision in revisions if revision.get("source_label") == "今回"),
        revisions[0] if revisions else {},
    )
    for product in _objects(metadata.get("products") or []):
        yj_code = product.get("yj_code")
        medicines.append(
            RegisteredMedicine(
                medicine=MedicineProduct(
                    yj_code=YjCode(_string(yj_code)) if yj_code is not None else None,
                    names=MedicineNames(
                        brand_name=BrandName(name)
                        if (name := _optional_name_text(product.get("brand_name")))
                        is not None
                        else None,
                        generic_name=GenericName(name)
                        if (name := _optional_name_text(metadata.get("generic_name")))
                        is not None
                        else None,
                        english_name=EnglishName(name)
                        if (name := _optional_name_text(product.get("english_name")))
                        is not None
                        else None,
                        hiragana_name=HiraganaName(name)
                        if (name := _optional_name_text(product.get("hiragana_name")))
                        is not None
                        else None,
                    ),
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
