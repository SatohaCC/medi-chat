"""原本から検索モデルへの技術非依存の明示投影。"""

from dataclasses import replace

from ...domain.attachment.entities import AttachmentDocument
from ...domain.attachment.exceptions import AttachmentDomainError
from ...domain.attachment.value_objects import (
    AttachmentBlock,
    AttachmentContext,
    AttachmentParagraph,
    AttachmentReference,
    AttachmentSection,
    AttachmentTableBlock,
)
from ...domain.medicine.identifiers import YjCode
from ...domain.retrieval.entities import SearchUnit
from ...domain.retrieval.identifiers import SearchUnitId
from ...domain.retrieval.primitives import (
    SearchUnitKind,
    SearchUnitProductCode,
    SearchUnitSectionCode,
    SearchUnitText,
    SearchUnitUrl,
)
from ...domain.retrieval.value_objects import (
    DocumentRevision,
    EvidenceReference,
    SearchContentBlock,
    SearchContentContext,
    SearchContentReference,
    SearchFigure,
    SearchParagraph,
    SearchTable,
    SearchTableBlock,
    SearchTableCell,
)


def _context(context: AttachmentContext) -> SearchContentContext:
    return SearchContentContext(
        product_codes=tuple(
            SearchUnitProductCode(code.value) for code in context.product_codes
        ),
        labels=tuple(SearchUnitText(label.value) for label in context.labels),
    )


def _references(
    references: tuple[AttachmentReference, ...],
) -> tuple[SearchContentReference, ...]:
    return tuple(
        SearchContentReference(
            label=SearchUnitText(reference.label.value),
            target_id=SearchUnitText(reference.target_id.value)
            if reference.target_id is not None
            else None,
            metadata=EvidenceReference(reference.metadata.to_dict()),
        )
        for reference in references
    )


def _block(block: AttachmentBlock) -> SearchContentBlock:
    context = _context(block.context)
    references = _references(block.references)
    if isinstance(block, AttachmentParagraph):
        return SearchParagraph(
            text=SearchUnitText(block.text.value),
            is_heading=block.is_heading,
            context=context,
            references=references,
        )
    if isinstance(block, AttachmentTableBlock):
        return SearchTableBlock(
            table=SearchTable(
                columns=tuple(
                    SearchUnitText(column.value) for column in block.table.columns
                ),
                rows=tuple(
                    tuple(
                        SearchTableCell(
                            text=SearchUnitText(cell.text.value),
                            column=cell.column.value,
                            rowspan=cell.rowspan.value,
                            colspan=cell.colspan.value,
                            references=_references(cell.references),
                            context=_context(cell.context),
                        )
                        for cell in row
                    )
                    for row in block.table.rows
                ),
            ),
            context=context,
            references=references,
        )
    return SearchFigure(
        reference=SearchUnitText(block.reference.value),
        description=SearchUnitText(block.description.value),
        context=context,
        references=references,
    )


def _text(block: SearchContentBlock) -> str:
    if isinstance(block, SearchParagraph):
        return block.text.value
    if isinstance(block, SearchTableBlock):
        return "\n".join(
            "\t".join(cell.text.value for cell in row) for row in block.table.rows
        )
    return block.description.value


def project_attachment(document: AttachmentDocument) -> tuple[SearchUnit, ...]:
    revisions = tuple(
        DocumentRevision(
            {
                "source_label": revision.source_label.value,
                "year_month": revision.year_month.value,
                "version": revision.version.value,
                "metadata": revision.metadata.to_dict(),
            }
        )
        for revision in document.revisions
    )
    units = []
    for section in document.sections:
        members = section.walk()
        blocks = tuple(
            replace(
                projected,
                context=replace(
                    projected.context,
                    section_code=SearchUnitSectionCode(member.code.value),
                    section_title=SearchUnitText(member.title.value),
                ),
            )
            for member in members
            if member.body is not None
            for block in member.body.blocks
            for projected in (_block(block),)
        )
        if not blocks:
            continue
        scoped_codes = {
            code for block in blocks for code in block.context.product_codes
        }
        if any(not block.context.product_codes for block in blocks):
            scoped_codes.update(
                SearchUnitProductCode(product.product_code.value)
                for product in document.products
            )
        product_codes = tuple(
            SearchUnitProductCode(product.product_code.value)
            for product in document.products
            if SearchUnitProductCode(product.product_code.value) in scoped_codes
        )
        units.append(
            SearchUnit(
                unit_id=SearchUnitId(
                    f"{document.document_id.value}:{section.code.value}"
                ),
                document_id=document.document_id,
                section_code=SearchUnitSectionCode(section.code.value),
                section_title=SearchUnitText(section.title.value),
                kind=SearchUnitKind("section"),
                text=SearchUnitText(
                    "\n\n".join(
                        (
                            f"{member.code.value} {member.title.value}\n\n"
                            if member is not section
                            else ""
                        )
                        + (
                            member.body.text.value
                            if member.body.text is not None
                            else "\n\n".join(
                                _text(_block(block)) for block in member.body.blocks
                            )
                        )
                        for member in members
                        if member.body is not None and member.body.blocks
                    )
                ),
                source_url=SearchUnitUrl(document.source.pmda_url.value),
                product_codes=product_codes,
                blocks=blocks,
                revisions=revisions,
            )
        )
    return tuple(units)


def project_active_attachment(
    document: AttachmentDocument, active_yj_codes: frozenset[YjCode]
) -> tuple[SearchUnit, ...]:
    """登録active範囲の版固定投影。"""
    if document.source.sha256 is None:
        raise AttachmentDomainError("registration source hash is required")
    active = {code.value for code in active_yj_codes}
    excluded_targets = {
        target.reference_id.value
        for target in document.reference_targets
        if target.context.product_codes
        and not any(code.value in active for code in target.context.product_codes)
    }

    def active_section(section: AttachmentSection) -> AttachmentSection:
        blocks = []
        for block in section.body.blocks if section.body is not None else ():
            block = replace(
                block,
                references=tuple(
                    reference
                    for reference in block.references
                    if reference.target_id is None
                    or reference.target_id.value not in excluded_targets
                ),
            )
            if isinstance(block, AttachmentTableBlock):
                block = _active_table(block, active, excluded_targets)
                if block is None:
                    continue
            codes = tuple(
                code for code in block.context.product_codes if code.value in active
            )
            if block.context.product_codes and not codes:
                continue
            blocks.append(
                replace(block, context=replace(block.context, product_codes=codes))
            )
        return replace(
            section,
            body=replace(section.body, blocks=tuple(blocks), text=None)
            if section.body is not None
            else None,
            children=tuple(active_section(child) for child in section.children),
        )

    sections = tuple(active_section(section) for section in document.sections)
    projected = project_attachment(replace(document, sections=tuple(sections)))
    return tuple(
        replace(
            unit,
            unit_id=SearchUnitId(
                f"{document.document_id.value}:{document.source.sha256.value}:{unit.section_code.value}"
            ),
            product_codes=tuple(
                SearchUnitProductCode(code.value)
                for code in sorted(active_yj_codes, key=lambda code: code.value)
            ),
        )
        for unit in projected
    )


def _active_table(
    block: AttachmentTableBlock, active: set[str], excluded_targets: set[str]
) -> AttachmentTableBlock | None:
    table = block.table

    def applies(context: AttachmentContext) -> bool:
        return not context.product_codes or any(
            code.value in active for code in context.product_codes
        )

    has_cell_scopes = any(
        cell.context.product_codes for row in table.rows for cell in row
    )
    if not has_cell_scopes and not applies(block.context):
        return None

    # Remove a grid column only when no retained source cell occupies it.
    # This uses explicit cell scopes without treating the first row as a heading.
    allowed = {
        column
        for row in table.rows
        for cell in row
        if applies(cell.context)
        for column in range(cell.column.value, cell.column.value + cell.colspan.value)
    }
    retained_headings = list(range(len(table.columns)))
    if (
        table.column_contexts
        and table.rows
        and len(table.rows[0]) == len(table.columns)
    ):
        retained_headings = [
            index
            for index, context in enumerate(table.column_contexts)
            if applies(context)
        ]
        excluded = set(range(len(table.columns))) - set(retained_headings)
        for index in excluded:
            heading = table.rows[0][index]
            allowed.difference_update(
                range(
                    heading.column.value, heading.column.value + heading.colspan.value
                )
            )
    coordinates = {old: new for new, old in enumerate(sorted(allowed))}
    rows = []
    for row in table.rows:
        cells = []
        for cell in row:
            columns = [
                column
                for column in range(
                    cell.column.value, cell.column.value + cell.colspan.value
                )
                if column in allowed
            ]
            if not columns or not applies(cell.context):
                continue
            cells.append(
                replace(
                    cell,
                    column=type(cell.column)(coordinates[columns[0]]),
                    colspan=type(cell.colspan)(len(columns)),
                    references=tuple(
                        reference
                        for reference in cell.references
                        if reference.target_id is None
                        or reference.target_id.value not in excluded_targets
                    ),
                    context=replace(
                        cell.context,
                        product_codes=tuple(
                            code
                            for code in cell.context.product_codes
                            if code.value in active
                        ),
                    ),
                )
            )
        rows.append(tuple(cells))
    if not any(rows):
        return None
    return replace(
        block,
        table=replace(
            table,
            columns=tuple(table.columns[index] for index in retained_headings),
            column_contexts=tuple(
                table.column_contexts[index] for index in retained_headings
            )
            if table.column_contexts
            else (),
            rows=tuple(rows),
        ),
        context=replace(
            block.context,
            product_codes=tuple(
                type(code)(code.value)
                for row in rows
                for cell in row
                for code in cell.context.product_codes
                if code.value in active
            )
            if has_cell_scopes
            else tuple(
                code for code in block.context.product_codes if code.value in active
            ),
        ),
        references=tuple(
            reference for row in rows for cell in row for reference in cell.references
        )
        if any(cell.references for row in table.rows for cell in row)
        else block.references,
    )
