import json

from ...application.attachment_import.import_errors import (
    ImportLimitExceeded,
    InvalidAttachment,
)
from ...application.attachment_import.import_models import (
    ArtifactBundle,
    ArtifactFile,
    ImportedProduct,
    ImportedRevision,
    ImportResult,
    ImportWarning,
)
from ...domain.attachment.entities import AttachmentDocument
from ...domain.retrieval.entities import SearchUnit
from ..index_payloads import (
    MAX_ARTIFACT_BYTES,
    json_bytes,
    result_dict,
    result_from_dict,
)
from .decoder import SourceInformation

__all__ = [
    "MAX_ARTIFACT_BYTES",
    "PmdaArtifactEncoder",
    "json_bytes",
    "result_dict",
    "result_from_dict",
]


class PmdaArtifactEncoder:
    transformer_version = "medi-chat.pmda-import.v1"

    def encode(
        self,
        document: AttachmentDocument,
        search_units: tuple[SearchUnit, ...],
        source_info: object,
    ) -> ArtifactBundle:
        if not isinstance(source_info, SourceInformation):
            raise InvalidAttachment(
                "invalid_source_information", "Source information is invalid"
            )
        info = source_info
        templates = {row["section"]["code"]: row for row in info.rows}
        rows = []
        units_by_code = {unit.section_code.value: unit for unit in search_units}
        if units_by_code.keys() != templates.keys():
            raise InvalidAttachment(
                "projection_mismatch", "Numbered body projection is incomplete"
            )
        for template in info.rows:
            unit = units_by_code[template["section"]["code"]]
            rows.append(
                {
                    "unit_id": unit.unit_id.value,
                    "document_key": unit.document_id.value,
                    "kind": unit.kind.value,
                    "section": template["section"],
                    "product_yj_codes": [code.value for code in unit.product_codes],
                    "text": unit.text.value,
                    "source": template["source"],
                    "references": template["references"],
                }
            )
        meta = info.document["document"]
        digest = info.document["source"]["sha256"]
        result = ImportResult(
            document_id=document.document_id.value,
            source_sha256=digest,
            validation_status=info.validation["status"],
            section_count=len(document.sections),
            search_unit_count=len(rows),
            products=tuple(
                ImportedProduct(product["yj_code"], product["brand_name"])
                for product in meta["products"]
            ),
            revisions=tuple(
                ImportedRevision(
                    revision["source_label"],
                    revision["year_month"],
                    revision["version"],
                )
                for revision in meta["revisions"]
            ),
            warnings=tuple(
                ImportWarning("missing_figure", filename)
                for filename in info.validation["missing_figures"]
            ),
            transformer_version=self.transformer_version,
        )
        files = (
            ArtifactFile("document.json", json_bytes(info.document)),
            ArtifactFile(
                "search_units.jsonl",
                "".join(
                    json.dumps(row, ensure_ascii=False) + "\n" for row in rows
                ).encode("utf-8"),
            ),
            ArtifactFile("validation.json", json_bytes(info.validation)),
            ArtifactFile(
                "source_metadata.json",
                json_bytes(
                    {
                        "schema_version": "medi-chat.pmda-source-metadata.v1",
                        "events": info.events,
                    }
                ),
            ),
            ArtifactFile("result.json", json_bytes(result_dict(result))),
        )
        if (
            sum(
                len(file.content)
                for file in files
                if file.name != "source_metadata.json"
            )
            > MAX_ARTIFACT_BYTES
        ):
            raise ImportLimitExceeded(
                "artifact_size_limit", "Generated artifacts exceed the size limit"
            )
        return ArtifactBundle(document.document_id, digest, files, result)
