"""Versioned, lossless attachment persistence boundary."""

from typing import Any

from backend.domain.attachment import primitives as p
from backend.domain.attachment import value_objects as v
from backend.domain.attachment.entities import AttachmentDocument
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.foundation.exceptions import DomainError

SCHEMA_VERSION = 1
TRANSFORMER_VERSION = "attachment-domain.v1"


def _context(value: v.AttachmentContext) -> dict[str, Any]:
    return {
        "product_codes": [code.value for code in value.product_codes],
        "labels": [label.value for label in value.labels],
        "source_order": value.source_order.value
        if value.source_order is not None
        else None,
    }


def _read_context(value: dict[str, Any]) -> v.AttachmentContext:
    return v.AttachmentContext(
        product_codes=tuple(
            p.AttachmentProductCode(code) for code in value["product_codes"]
        ),
        labels=tuple(p.AttachmentText(label) for label in value["labels"]),
        source_order=p.AttachmentSourceOrder(value["source_order"])
        if value["source_order"] is not None
        else None,
    )


def _reference(value: v.AttachmentReference) -> dict[str, Any]:
    return {
        "label": value.label.value,
        "target_id": value.target_id.value if value.target_id is not None else None,
        "metadata": value.metadata.to_dict(),
    }


def _read_reference(value: dict[str, Any]) -> v.AttachmentReference:
    return v.AttachmentReference(
        label=p.AttachmentText(value["label"]),
        target_id=p.AttachmentText(value["target_id"])
        if value["target_id"] is not None
        else None,
        metadata=v.AttachmentMetadata(value["metadata"]),
    )


def _cell(value: v.AttachmentTableCell) -> dict[str, Any]:
    return {
        "text": value.text.value,
        "column": value.column.value,
        "rowspan": value.rowspan.value,
        "colspan": value.colspan.value,
        "references": [_reference(ref) for ref in value.references],
        "context": _context(value.context),
    }


def _read_cell(value: dict[str, Any]) -> v.AttachmentTableCell:
    return v.AttachmentTableCell(
        text=p.AttachmentText(value["text"]),
        column=p.AttachmentColumnIndex(value["column"]),
        rowspan=p.AttachmentCellSpan(value["rowspan"]),
        colspan=p.AttachmentCellSpan(value["colspan"]),
        references=tuple(_read_reference(ref) for ref in value["references"]),
        context=_read_context(value["context"]),
    )


def _block(value: v.AttachmentBlock) -> dict[str, Any]:
    common = {
        "context": _context(value.context),
        "references": [_reference(ref) for ref in value.references],
    }
    if isinstance(value, v.AttachmentParagraph):
        return {
            **common,
            "kind": "paragraph",
            "text": value.text.value,
            "is_heading": value.is_heading,
        }
    if isinstance(value, v.AttachmentFigure):
        return {
            **common,
            "kind": "figure",
            "reference": value.reference.value,
            "description": value.description.value,
        }
    return {
        **common,
        "kind": "table",
        "table": {
            "columns": [column.value for column in value.table.columns],
            "column_contexts": [
                _context(context) for context in value.table.column_contexts
            ],
            "rows": [[_cell(cell) for cell in row] for row in value.table.rows],
        },
    }


def _read_block(value: dict[str, Any]) -> v.AttachmentBlock:
    context = _read_context(value["context"])
    references = tuple(_read_reference(ref) for ref in value["references"])
    if value["kind"] == "paragraph":
        if type(value["is_heading"]) is not bool:
            raise ValueError("paragraph heading must be boolean")
        return v.AttachmentParagraph(
            text=p.AttachmentText(value["text"]),
            is_heading=value["is_heading"],
            context=context,
            references=references,
        )
    if value["kind"] == "figure":
        return v.AttachmentFigure(
            reference=p.AttachmentText(value["reference"]),
            description=p.AttachmentText(value["description"]),
            context=context,
            references=references,
        )
    if value["kind"] != "table":
        raise ValueError("unknown attachment block kind")
    table = value["table"]
    return v.AttachmentTableBlock(
        context=context,
        references=references,
        table=v.AttachmentTable(
            columns=tuple(p.AttachmentText(column) for column in table["columns"]),
            column_contexts=tuple(
                _read_context(context) for context in table["column_contexts"]
            ),
            rows=tuple(
                tuple(_read_cell(cell) for cell in row) for row in table["rows"]
            ),
        ),
    )


def _section(value: v.AttachmentSection) -> dict[str, Any]:
    return {
        "code": value.code.value,
        "title": value.title.value,
        "header": value.header.value if value.header is not None else None,
        "body": {
            "text": value.body.text.value if value.body.text is not None else None,
            "blocks": [_block(block) for block in value.body.blocks],
        }
        if value.body is not None
        else None,
        "children": [_section(child) for child in value.children],
    }


def _read_section(value: dict[str, Any]) -> v.AttachmentSection:
    body = value["body"]
    return v.AttachmentSection(
        code=p.NumberedSectionCode(value["code"]),
        title=p.AttachmentSectionTitle(value["title"]),
        header=p.AttachmentText(value["header"])
        if value["header"] is not None
        else None,
        body=v.AttachmentBody(
            text=p.AttachmentText(body["text"]) if body["text"] is not None else None,
            blocks=tuple(_read_block(block) for block in body["blocks"]),
        )
        if body is not None
        else None,
        children=tuple(_read_section(child) for child in value["children"]),
    )


def document_to_payload(document: AttachmentDocument) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "transformer_version": TRANSFORMER_VERSION,
        "document": {
            "document_id": document.document_id.value,
            "source": {
                "pmda_url": document.source.pmda_url.value,
                "sha256": document.source.sha256.value
                if document.source.sha256 is not None
                else None,
            },
            "products": [
                {
                    "product_code": product.product_code.value,
                    "brand_name": product.brand_name.value,
                    "english_name": product.english_name.value
                    if product.english_name is not None
                    else None,
                }
                for product in document.products
            ],
            "revisions": [
                {
                    "source_label": revision.source_label.value,
                    "year_month": revision.year_month.value,
                    "version": revision.version.value,
                    "metadata": revision.metadata.to_dict(),
                }
                for revision in document.revisions
            ],
            "sections": [_section(section) for section in document.sections],
            "reference_targets": [
                {
                    "reference_id": target.reference_id.value,
                    "text": target.text.value,
                    "context": _context(target.context),
                }
                for target in document.reference_targets
            ],
        },
    }


def document_from_payload(payload: dict[str, Any]) -> AttachmentDocument:
    try:
        if (
            type(payload["schema_version"]) is not int
            or payload["schema_version"] != SCHEMA_VERSION
            or payload["transformer_version"] != TRANSFORMER_VERSION
        ):
            raise ValueError("unsupported attachment schema or transformer version")
        value = payload["document"]
        document = AttachmentDocument(
            document_id=DocumentId(value["document_id"]),
            source=v.AttachmentSource(
                p.AttachmentUrl(value["source"]["pmda_url"]),
                p.AttachmentSha256(value["source"]["sha256"])
                if value["source"]["sha256"] is not None
                else None,
            ),
            products=tuple(
                v.AttachmentProduct(
                    p.AttachmentProductCode(product["product_code"]),
                    p.AttachmentBrandName(product["brand_name"]),
                    p.AttachmentEnglishName(product["english_name"])
                    if product["english_name"] is not None
                    else None,
                )
                for product in value["products"]
            ),
            revisions=tuple(
                v.AttachmentRevision(
                    p.RevisionSourceLabel(revision["source_label"]),
                    p.RevisionYearMonth(revision["year_month"]),
                    p.RevisionVersion(revision["version"]),
                    v.AttachmentMetadata(revision["metadata"]),
                )
                for revision in value["revisions"]
            ),
            sections=tuple(_read_section(section) for section in value["sections"]),
            reference_targets=tuple(
                v.AttachmentReferenceTarget(
                    reference_id=p.AttachmentText(target["reference_id"]),
                    text=p.AttachmentText(target["text"]),
                    context=_read_context(target["context"]),
                )
                for target in value["reference_targets"]
            ),
        )
        return document
    except (KeyError, TypeError, AttributeError, DomainError) as error:
        raise ValueError("invalid stored attachment structure") from error
