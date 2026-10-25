"""Render search payload blocks into HTML search text."""

from __future__ import annotations

import html

from backend.domain.foundation.json_types import JsonValue
from backend.infrastructure.serialization.json_payload_values import (
    _object,
    _objects,
    _string,
    _strings,
)


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
