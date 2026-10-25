import hashlib
from dataclasses import replace
from pathlib import PurePosixPath
from typing import Any

from backend.application.attachment_import.errors import InvalidAttachment
from backend.domain.attachment.entities import AttachmentDocument
from backend.domain.attachment.exceptions import AttachmentDomainError
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.attachment.primitives import (
    AttachmentBrandName,
    AttachmentCellSpan,
    AttachmentColumnIndex,
    AttachmentEnglishName,
    AttachmentProductCode,
    AttachmentSectionTitle,
    AttachmentSha256,
    AttachmentSourceOrder,
    AttachmentText,
    AttachmentUrl,
    NumberedSectionCode,
    RevisionSourceLabel,
    RevisionVersion,
    RevisionYearMonth,
)
from backend.domain.attachment.value_objects import (
    AttachmentBlock,
    AttachmentBody,
    AttachmentContext,
    AttachmentFigure,
    AttachmentMetadata,
    AttachmentParagraph,
    AttachmentProduct,
    AttachmentReference,
    AttachmentReferenceTarget,
    AttachmentRevision,
    AttachmentSection,
    AttachmentSource,
    AttachmentTable,
    AttachmentTableBlock,
    AttachmentTableCell,
)
from backend.domain.foundation.exceptions import DomainValidationError
from backend.infrastructure.document_import.attachment_payloads import (
    AttachmentSourceInformation,
    DecodedAttachment,
)
from backend.infrastructure.package_insert_definitions.definition_assembly import (
    get_package_insert_definitions,
)
from backend.infrastructure.package_insert_definitions.definition_settings import (
    PmdaXmlSettings,
)
from backend.infrastructure.pmda_xml.artifact_builder import build_artifacts
from backend.infrastructure.pmda_xml.search_unit_mapping import (
    _make_fragments,
    _scoped_products,
    context_labels,
)
from backend.infrastructure.pmda_xml.section_mapping import (
    make_section_index,
    reference_section_code,
)
from backend.infrastructure.pmda_xml.xml_node_mapping import (
    build_paths,
    direct_child,
    tag_name,
    text_of,
)
from backend.infrastructure.pmda_xml.xml_safe_parser import parse_source


def _context(fragment: dict[str, Any]) -> AttachmentContext:
    return AttachmentContext(
        product_codes=tuple(
            AttachmentProductCode(code) for code in fragment["product_yj_codes"]
        ),
        labels=tuple(AttachmentText(label) for label in fragment["context_labels"]),
        source_order=AttachmentSourceOrder(order)
        if (order := fragment.get("source_order")) is not None
        else None,
    )


def _references(fragment: dict[str, Any]) -> tuple[AttachmentReference, ...]:
    return tuple(
        AttachmentReference(
            label=AttachmentText(reference["kind"]),
            target_id=AttachmentText(reference["target_xml_id"])
            if reference["target_xml_id"] is not None
            else None,
            metadata=AttachmentMetadata(
                {
                    key: reference[key]
                    for key in ("kind", "target_section_code", "target_url")
                }
            ),
        )
        for reference in fragment["references"]
    )


def _blocks(
    fragments: list[dict[str, Any]],
    cell_details: dict[
        str, tuple[tuple[AttachmentContext, tuple[AttachmentReference, ...]], ...]
    ]
    | None = None,
    *,
    xml_settings: PmdaXmlSettings | None = None,
) -> tuple[AttachmentBlock, ...]:
    if xml_settings is None:
        xml_settings = get_package_insert_definitions().xml_settings

    blocks: list[AttachmentBlock] = []
    table_key = None
    previous_order = None
    for fragment in fragments:
        kind = fragment["kind"]
        context = _context(fragment)
        adjacent = (
            previous_order is None
            or context.source_order is None
            or context.source_order.value == previous_order + 1
        )
        references = _references(fragment)
        key = None
        columns: tuple[AttachmentText, ...] = ()
        cells: tuple[AttachmentTableCell, ...] = ()
        if kind == "interaction_row":
            columns = tuple(
                AttachmentText(column.title)
                for column in xml_settings.interaction_columns
            )
            cells = tuple(
                AttachmentTableCell(
                    text=AttachmentText(fragment["columns"][column.id]),
                    column=AttachmentColumnIndex(index),
                )
                for index, column in enumerate(xml_settings.interaction_columns)
            )
            key = kind
        elif kind == "adverse_reaction_cell":
            columns = tuple(
                AttachmentText(label) for label in ("分類", "頻度", "副作用")
            )
            cells = tuple(
                AttachmentTableCell(
                    text=AttachmentText(text), column=AttachmentColumnIndex(index)
                )
                for index, text in enumerate(
                    (
                        fragment["category"]["label"] or "",
                        fragment["frequency"]["label"] or "",
                        fragment["text"],
                    )
                )
            )
            key = kind
        elif kind == "table_row":
            cells_list = []
            occupied: set[int] = set()
            previous = blocks[-1] if blocks else None
            if (
                table_key == fragment["table_xml_path"]
                and isinstance(previous, AttachmentTableBlock)
                and previous.context == context
                and adjacent
            ):
                current_row = len(previous.table.rows)
                for row_index, row in enumerate(previous.table.rows):
                    for cell in row:
                        if row_index + cell.rowspan.value > current_row:
                            occupied.update(
                                range(
                                    cell.column.value,
                                    cell.column.value + cell.colspan.value,
                                )
                            )
            column = 0
            details = (cell_details or {}).get(
                fragment["table_xml_path"]
                + ":"
                + str(fragment["row_index_zero_based"]),
                (),
            )
            for cell_index, cell in enumerate(fragment["cells"]):
                while column in occupied:
                    column += 1
                colspan = int(cell["attributes"].get("cspan", "1"))
                cells_list.append(
                    AttachmentTableCell(
                        text=AttachmentText(cell["text"]),
                        column=AttachmentColumnIndex(column),
                        rowspan=AttachmentCellSpan(
                            int(cell["attributes"].get("rspan", "1"))
                        ),
                        colspan=AttachmentCellSpan(colspan),
                        context=details[cell_index][0] if details else context,
                        references=details[cell_index][1] if details else (),
                    )
                )
                column += colspan
            cells = tuple(cells_list)
            key = fragment["table_xml_path"]
        if key is not None:
            previous = blocks[-1] if blocks else None
            if (
                table_key == key
                and isinstance(previous, AttachmentTableBlock)
                and previous.context == context
                and adjacent
            ):
                blocks[-1] = replace(
                    previous,
                    table=replace(previous.table, rows=previous.table.rows + (cells,)),
                    references=previous.references + references,
                )
            else:
                blocks.append(
                    AttachmentTableBlock(
                        table=AttachmentTable(
                            columns=columns,
                            rows=(cells,),
                            column_contexts=tuple(cell.context for cell in cells)
                            if columns and len(columns) == len(cells)
                            else (),
                        ),
                        context=context,
                        references=references,
                    )
                )
        elif kind == "graphic":
            name = fragment["text"].split("\n", 1)[0].removeprefix("図ファイル: ")
            blocks.append(
                AttachmentFigure(
                    reference=AttachmentText(name),
                    description=AttachmentText("\n".join(fragment["figure_captions"])),
                    context=context,
                    references=references,
                )
            )
        else:
            blocks.append(
                AttachmentParagraph(
                    text=AttachmentText(fragment["text"]),
                    is_heading=kind == "header",
                    context=context,
                    references=references,
                )
            )
        table_key = key
        previous_order = (
            context.source_order.value if context.source_order is not None else None
        )
    return tuple(blocks)


class PmdaXmlDecoder:
    def __init__(
        self,
        *,
        xml_settings: PmdaXmlSettings | None = None,
        assets: dict[str, bytes] | None = None,
        strict_assets: bool = False,
        source_filename: str | None = None,
    ) -> None:
        self._xml_settings = (
            xml_settings
            if xml_settings is not None
            else get_package_insert_definitions().xml_settings
        )
        self.assets = assets or {}
        self.strict_assets = strict_assets
        self.source_filename = source_filename

    def decode(
        self, source: bytes, *, original_filename: str = "source.xml"
    ) -> DecodedAttachment:
        xml_settings = self._xml_settings
        root, events = parse_source(source)
        ids = [
            element.attrib["id"] for element in root.iter() if "id" in element.attrib
        ]
        if len(ids) != len(set(ids)):
            raise InvalidAttachment(
                "duplicate_reference_id", "Original reference IDs are ambiguous"
            )
        filename = self.source_filename or original_filename
        if self.source_filename is not None:
            from backend.project_paths import PROJECT_ROOT

            filename = (
                str(
                    PurePosixPath(filename).relative_to(
                        PurePosixPath(PROJECT_ROOT.as_posix())
                    )
                )
                if PurePosixPath(filename).is_relative_to(
                    PurePosixPath(PROJECT_ROOT.as_posix())
                )
                else filename
            )
        digest = hashlib.sha256(source).hexdigest()
        document, rows, validation = build_artifacts(
            root,
            source_filename=filename,
            source_sha256=digest,
            assets=self.assets,
            strict_assets=self.strict_assets,
            xml_settings=xml_settings,
        )
        parents, paths = build_paths(root)
        _, by_element = make_section_index(
            root,
            parents,
            paths,
            document["source"]["pmda_url"],
            xml_settings=xml_settings,
        )
        codes = [section["code"] for section in document["section_index"]]
        if len(codes) != len(set(codes)):
            raise InvalidAttachment("duplicate_section", "Duplicate numbered section")
        fragments, _ = _make_fragments(
            root,
            parents,
            paths,
            by_element,
            document["source"]["pmda_url"],
            document["document"]["products"],
            xml_settings=xml_settings,
        )
        reference_elements = {
            element.attrib["id"]: element
            for element in root.iter()
            if "id" in element.attrib
        }
        for fragment in fragments:
            for reference in fragment["references"]:
                target = reference_elements.get(reference["target_xml_id"])
                if target is not None:
                    reference["target_section_code"] = reference_section_code(
                        target, parents, by_element, xml_settings=xml_settings
                    )
        grouped: dict[str, list[dict[str, Any]]] = {}
        for source_order, fragment in enumerate(fragments):
            fragment["source_order"] = source_order
            grouped.setdefault(fragment["section"]["code"], []).append(fragment)
        rows_by_code = {row["section"]["code"]: row for row in rows}
        meta = document["document"]
        products_by_id = {
            product["xml_id"]: product
            for product in meta["products"]
            if product.get("xml_id")
        }
        cell_details = {}
        ids_by_id = {
            element.attrib["id"]: element
            for element in root.iter()
            if "id" in element.attrib
        }

        for table in root.iter():
            if tag_name(table) not in {"SimpTbl", "SimpleTable"}:
                continue
            for row_index, row in enumerate(
                child for child in table if tag_name(child) == "SimpTblRow"
            ):
                details = []
                for cell in (
                    child for child in row if tag_name(child) == "SimpTblCell"
                ):
                    labels = context_labels(cell, parents, xml_settings=xml_settings)
                    products = _scoped_products(
                        cell, [cell], parents, meta["products"], products_by_id, labels
                    )
                    references = []
                    for child in cell.iter():
                        if tag_name(child) not in xml_settings.reference_tags:
                            continue
                        target_id = child.attrib.get("ref")
                        target = ids_by_id.get(target_id) if target_id else None
                        references.append(
                            AttachmentReference(
                                label=AttachmentText(tag_name(child)),
                                target_id=AttachmentText(target_id)
                                if target_id
                                else None,
                                metadata=AttachmentMetadata(
                                    {
                                        "kind": tag_name(child),
                                        "target_section_code": reference_section_code(
                                            target,
                                            parents,
                                            by_element,
                                            xml_settings=xml_settings,
                                        )
                                        if target is not None
                                        else None,
                                        "target_url": f"{document['source']['pmda_url']}#{target_id}"
                                        if target_id
                                        else None,
                                    }
                                ),
                            )
                        )
                    details.append(
                        (
                            AttachmentContext(
                                product_codes=tuple(
                                    AttachmentProductCode(product["yj_code"])
                                    for product in products
                                    if product.get("yj_code")
                                ),
                                labels=tuple(AttachmentText(label) for label in labels),
                            ),
                            tuple(references),
                        )
                    )
                cell_details[paths[table] + ":" + str(row_index)] = tuple(details)

        def section_model(section: dict[str, Any]) -> AttachmentSection:
            code = section["code"]
            element = next(
                element
                for element, value in by_element.items()
                if value["code"] == code
            )
            header = direct_child(element, "Header")
            return AttachmentSection(
                NumberedSectionCode(code),
                AttachmentSectionTitle(section["title"]),
                AttachmentBody(
                    blocks=_blocks(
                        grouped.get(code, []), cell_details, xml_settings=xml_settings
                    ),
                    text=AttachmentText(rows_by_code[code]["text"])
                    if code in rows_by_code
                    else None,
                ),
                header=AttachmentText(text_of(header, xml_settings=xml_settings))
                if header is not None
                else None,
                children=tuple(
                    section_model(child)
                    for child in document["section_index"]
                    if child["parent_code"] == code
                ),
            )

        try:
            model = AttachmentDocument(
                document_id=DocumentId(validation["document_key"]),
                source=AttachmentSource(
                    AttachmentUrl(document["source"]["pmda_url"]),
                    AttachmentSha256(digest),
                ),
                revisions=tuple(
                    AttachmentRevision(
                        RevisionSourceLabel(revision["source_label"] or "revision"),
                        RevisionYearMonth(revision["year_month"]),
                        RevisionVersion(revision["version"] or "unknown"),
                    )
                    for revision in meta["revisions"]
                ),
                products=tuple(
                    AttachmentProduct(
                        AttachmentProductCode(
                            product["yj_code"]
                            or product["xml_id"]
                            or f"product-{index}"
                        ),
                        AttachmentBrandName(
                            product["brand_name"]
                            or product["yj_code"]
                            or product["xml_id"]
                        ),
                        AttachmentEnglishName(product["english_name"])
                        if product["english_name"]
                        else None,
                    )
                    for index, product in enumerate(meta["products"])
                ),
                sections=tuple(
                    section_model(section)
                    for section in document["section_index"]
                    if section["parent_code"] is None
                ),
                reference_targets=tuple(
                    AttachmentReferenceTarget(
                        reference_id=AttachmentText(element.attrib["id"]),
                        text=AttachmentText(
                            text_of(element, xml_settings=xml_settings)
                        ),
                        context=AttachmentContext(
                            product_codes=tuple(
                                AttachmentProductCode(product["yj_code"])
                                for product in _scoped_products(
                                    element,
                                    [element],
                                    parents,
                                    meta["products"],
                                    products_by_id,
                                    context_labels(
                                        element, parents, xml_settings=xml_settings
                                    ),
                                )
                                if product.get("yj_code")
                            ),
                            labels=tuple(
                                AttachmentText(label)
                                for label in context_labels(
                                    element, parents, xml_settings=xml_settings
                                )
                            ),
                        ),
                    )
                    for element in root.iter()
                    if "id" in element.attrib
                ),
            )
        except (
            AttachmentDomainError,
            DomainValidationError,
            ValueError,
            TypeError,
        ):
            raise InvalidAttachment(
                "invalid_document_structure", "Original document structure is invalid"
            ) from None
        return DecodedAttachment(
            model, AttachmentSourceInformation(document, rows, validation, events)
        )
