"""Versioned, lossless package_insert persistence boundary."""

from typing import Any

from backend.domain.foundation.exceptions import DomainError
from backend.domain.package_insert import primitives as p
from backend.domain.package_insert import value_objects as v
from backend.domain.package_insert.entities import PackageInsertDocument
from backend.domain.package_insert.identifiers import DocumentId

SCHEMA_VERSION = 1
TRANSFORMER_VERSION = "package-insert-domain.v1"


def _context(value: v.PackageInsertContext) -> dict[str, Any]:
    return {
        "product_codes": [code.value for code in value.product_codes],
        "labels": [label.value for label in value.labels],
        "source_order": value.source_order.value
        if value.source_order is not None
        else None,
    }


def _read_context(value: dict[str, Any]) -> v.PackageInsertContext:
    return v.PackageInsertContext(
        product_codes=tuple(
            p.PackageInsertProductCode(code) for code in value["product_codes"]
        ),
        labels=tuple(p.PackageInsertText(label) for label in value["labels"]),
        source_order=p.PackageInsertSourceOrder(value["source_order"])
        if value["source_order"] is not None
        else None,
    )


def _reference(value: v.PackageInsertReference) -> dict[str, Any]:
    return {
        "label": value.label.value,
        "target_id": value.target_id.value if value.target_id is not None else None,
        "metadata": value.metadata.to_dict(),
    }


def _read_reference(value: dict[str, Any]) -> v.PackageInsertReference:
    return v.PackageInsertReference(
        label=p.PackageInsertText(value["label"]),
        target_id=p.PackageInsertText(value["target_id"])
        if value["target_id"] is not None
        else None,
        metadata=v.PackageInsertMetadata(value["metadata"]),
    )


def _cell(value: v.PackageInsertTableCell) -> dict[str, Any]:
    return {
        "text": value.text.value,
        "column": value.column.value,
        "rowspan": value.rowspan.value,
        "colspan": value.colspan.value,
        "references": [_reference(ref) for ref in value.references],
        "context": _context(value.context),
    }


def _read_cell(value: dict[str, Any]) -> v.PackageInsertTableCell:
    return v.PackageInsertTableCell(
        text=p.PackageInsertText(value["text"]),
        column=p.PackageInsertColumnIndex(value["column"]),
        rowspan=p.PackageInsertCellSpan(value["rowspan"]),
        colspan=p.PackageInsertCellSpan(value["colspan"]),
        references=tuple(_read_reference(ref) for ref in value["references"]),
        context=_read_context(value["context"]),
    )


def _block(value: v.PackageInsertBlock) -> dict[str, Any]:
    common = {
        "context": _context(value.context),
        "references": [_reference(ref) for ref in value.references],
    }
    if isinstance(value, v.PackageInsertParagraph):
        return {
            **common,
            "kind": "paragraph",
            "text": value.text.value,
            "is_heading": value.is_heading,
        }
    if isinstance(value, v.PackageInsertFigure):
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


def _read_block(value: dict[str, Any]) -> v.PackageInsertBlock:
    context = _read_context(value["context"])
    references = tuple(_read_reference(ref) for ref in value["references"])
    if value["kind"] == "paragraph":
        if type(value["is_heading"]) is not bool:
            raise ValueError("paragraph heading must be boolean")
        return v.PackageInsertParagraph(
            text=p.PackageInsertText(value["text"]),
            is_heading=value["is_heading"],
            context=context,
            references=references,
        )
    if value["kind"] == "figure":
        return v.PackageInsertFigure(
            reference=p.PackageInsertText(value["reference"]),
            description=p.PackageInsertText(value["description"]),
            context=context,
            references=references,
        )
    if value["kind"] != "table":
        raise ValueError("unknown package_insert block kind")
    table = value["table"]
    return v.PackageInsertTableBlock(
        context=context,
        references=references,
        table=v.PackageInsertTable(
            columns=tuple(p.PackageInsertText(column) for column in table["columns"]),
            column_contexts=tuple(
                _read_context(context) for context in table["column_contexts"]
            ),
            rows=tuple(
                tuple(_read_cell(cell) for cell in row) for row in table["rows"]
            ),
        ),
    )


def _section(value: v.PackageInsertSection) -> dict[str, Any]:
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


def _read_section(value: dict[str, Any]) -> v.PackageInsertSection:
    body = value["body"]
    return v.PackageInsertSection(
        code=p.NumberedSectionCode(value["code"]),
        title=p.PackageInsertSectionTitle(value["title"]),
        header=p.PackageInsertText(value["header"])
        if value["header"] is not None
        else None,
        body=v.PackageInsertBody(
            text=p.PackageInsertText(body["text"])
            if body["text"] is not None
            else None,
            blocks=tuple(_read_block(block) for block in body["blocks"]),
        )
        if body is not None
        else None,
        children=tuple(_read_section(child) for child in value["children"]),
    )


def document_to_payload(document: PackageInsertDocument) -> dict[str, Any]:
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


def document_from_payload(payload: dict[str, Any]) -> PackageInsertDocument:
    try:
        if (
            type(payload["schema_version"]) is not int
            or payload["schema_version"] != SCHEMA_VERSION
            or payload["transformer_version"] != TRANSFORMER_VERSION
        ):
            raise ValueError("unsupported package_insert schema or transformer version")
        value = payload["document"]
        document = PackageInsertDocument(
            document_id=DocumentId(value["document_id"]),
            source=v.PackageInsertSource(
                p.PackageInsertUrl(value["source"]["pmda_url"]),
                p.PackageInsertSha256(value["source"]["sha256"])
                if value["source"]["sha256"] is not None
                else None,
            ),
            products=tuple(
                v.PackageInsertProduct(
                    p.PackageInsertProductCode(product["product_code"]),
                    p.PackageInsertBrandName(product["brand_name"]),
                    p.PackageInsertEnglishName(product["english_name"])
                    if product["english_name"] is not None
                    else None,
                )
                for product in value["products"]
            ),
            revisions=tuple(
                v.PackageInsertRevision(
                    p.RevisionSourceLabel(revision["source_label"]),
                    p.RevisionYearMonth(revision["year_month"]),
                    p.RevisionVersion(revision["version"]),
                    v.PackageInsertMetadata(revision["metadata"]),
                )
                for revision in value["revisions"]
            ),
            sections=tuple(_read_section(section) for section in value["sections"]),
            reference_targets=tuple(
                v.PackageInsertReferenceTarget(
                    reference_id=p.PackageInsertText(target["reference_id"]),
                    text=p.PackageInsertText(target["text"]),
                    context=_read_context(target["context"]),
                )
                for target in value["reference_targets"]
            ),
        )
        return document
    except (KeyError, TypeError, AttributeError, DomainError) as error:
        raise ValueError("invalid stored package_insert structure") from error
