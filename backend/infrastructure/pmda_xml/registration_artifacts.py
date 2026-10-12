"""版固定active検索投影のv3保存境界。旧v2生成物を書き換えない。"""

import html
import json
from typing import Any

from ...domain.attachment.entities import AttachmentDocument
from ...domain.retrieval.entities import SearchUnit
from ...domain.retrieval.value_objects import (
    SearchContentBlock,
    SearchContentReference,
    SearchParagraph,
    SearchTableBlock,
)


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
