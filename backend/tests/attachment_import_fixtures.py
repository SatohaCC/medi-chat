"""Handwritten PMDA inputs and independent artifact readers."""

import json

from backend.application.indexing.attachment_projection import project_attachment
from backend.infrastructure.pmda_xml.artifact_mapping import PmdaArtifactEncoder
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder


def xml_source(
    body="<Warnings><Detail><Lang> 警告 Ａ① </Lang></Detail></Warnings>",
    *,
    prefix="",
    encoding="utf-8",
):
    text = (
        prefix
        + '<PackIns drugType="Medicine"><CompanyIdentifier>000001</CompanyIdentifier><PackageInsertNo>test</PackageInsertNo><DateOfPreparationOrRevision><PreparationOrRevision id="今回"><YearMonth>2026-10</YearMonth><Version>1</Version></PreparationOrRevision></DateOfPreparationOrRevision><ApprovalEtc><DetailBrandName id="A"><ApprovalBrandName><Lang>製品A</Lang></ApprovalBrandName><BrandCode><YJCode>111111111111</YJCode></BrandCode></DetailBrandName></ApprovalEtc>'
        + body
        + "</PackIns>"
    )
    return text.encode(encoding)


def encoded(source, filename="source.xml", *, decoder=None, encoder=None):
    decoded = (decoder or PmdaXmlDecoder()).decode(source, original_filename=filename)
    return (encoder or PmdaArtifactEncoder()).encode(
        decoded.document, project_attachment(decoded.document), decoded.source_info
    )


def json_artifact(bundle, name):
    return json.loads(next(file.content for file in bundle.files if file.name == name))
