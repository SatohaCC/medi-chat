"""TC19/21: one explicitly projected definition version through every XML entry."""

import hashlib
import json
import sqlite3
from dataclasses import replace
from importlib import import_module

import httpx
import pytest
from backend.application.indexing.attachment_projection import project_attachment
from backend.application.medicine.product_models import ResolvedMedicine
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.medicine.value_objects import MedicineMatch as DomainMedicineMatch
from backend.domain.retrieval.primitives import DetectionSource, SearchSectionCode
from backend.domain.retrieval.value_objects import SearchCriteria
from backend.infrastructure.package_insert_definitions import loader
from backend.infrastructure.persistence.attachment_import_store import (
    FileAttachmentImportStore,
)
from backend.infrastructure.persistence.generation_runtime import GenerationRuntime
from backend.infrastructure.persistence.read_workers import ReadWorkers
from backend.infrastructure.persistence.registration_publisher import (
    SqliteRegistrationPublisher,
)
from backend.infrastructure.pmda_xml.artifact_mapping import PmdaArtifactEncoder
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.infrastructure.pmda_xml.transform import transform
from backend.tests.attachment_import_fixtures import xml_source
from backend.tests.test_alembic_migrations import _migrate_database


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "entrypoint", ["transform", "decoder_encoder", "publisher_materialize", "web"]
)
async def test_tc19_all_entries_keep_injected_definition_without_reload(
    tmp_path, monkeypatch, entrypoint
):
    data = json.loads(loader.DEFINITIONS_PATH.read_text(encoding="utf-8"))
    data["sections"]["27"] = {
        "title": "追加項目の正式名称",
        "xml_tags": ["SupplementarySection"],
    }
    data["intents"]["supplementary"] = {"sections": ["27"]}
    data["interaction_columns"][0]["title"] = "注入薬剤列"
    path = tmp_path / "definitions.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    definitions = loader.load_package_insert_definitions(path)
    source = xml_source(
        "<SupplementarySection><Detail><Lang>追補の原文本文</Lang></Detail></SupplementarySection><Interactions><ContraIndicatedCombinations><Drug><DrugName><Lang>相手薬の原文</Lang></DrugName></Drug></ContraIndicatedCombinations></Interactions>"
    ).replace(b"2026-10", b"2026-11")
    decoder = PmdaXmlDecoder(xml_settings=definitions.xml_settings)
    encoder = PmdaArtifactEncoder()
    structured = tmp_path / "structured"
    structured.mkdir()
    index = tmp_path / "index.sqlite3"
    _migrate_database(index, structured)
    store = FileAttachmentImportStore(tmp_path / "imports")
    publisher = SqliteRegistrationPublisher(
        index, store, xml_settings=definitions.xml_settings
    )
    workers = ReadWorkers()
    runtime = GenerationRuntime(
        publisher,
        workers=workers,
        text_search_policy=definitions.text_search_policy,
        xml_settings=definitions.xml_settings,
    )
    app = None
    if entrypoint == "web":
        from backend import main

        # Composition's first load is allowed; every use after this point is forbidden.
        monkeypatch.setattr(main, "get_package_insert_definitions", lambda: definitions)
        publisher.publish(
            decoder.decode(
                xml_source("<Warnings><Detail><Lang>旧原文</Lang></Detail></Warnings>")
            ),
            xml_source("<Warnings><Detail><Lang>旧原文</Lang></Detail></Warnings>"),
        )
        app = main.create_app(structured, index, import_directory=store.root)

    def forbid(*args, **kwargs):
        pytest.fail("explicit XML definition returned to loader/getter")

    for name in (
        "backend.main",
        "backend.infrastructure.package_insert_definitions.loader",
        "backend.infrastructure.pmda_xml.artifacts",
        "backend.infrastructure.pmda_xml.decoder",
        "backend.infrastructure.pmda_xml.sections",
        "backend.infrastructure.pmda_xml.units",
        "backend.infrastructure.pmda_xml.xml_nodes",
        "backend.infrastructure.pmda_xml.transform",
        "backend.infrastructure.persistence.generation_runtime",
        "backend.infrastructure.persistence.registration_publisher",
        "backend.infrastructure.persistence.evidence_reader",
        "backend.infrastructure.intent.jev_classifier",
    ):
        monkeypatch.setattr(
            import_module(name), "get_package_insert_definitions", forbid, raising=False
        )
    monkeypatch.setattr(loader, "load_package_insert_definitions", forbid)
    try:
        if entrypoint == "transform":
            xml = tmp_path / "source.xml"
            xml.write_bytes(source)
            output = tmp_path / "output"
            transform(xml, output, xml_settings=definitions.xml_settings)
            rows = [
                json.loads(line)
                for line in (output / "search_units.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
        elif entrypoint == "decoder_encoder":
            decoded = decoder.decode(source)
            bundle = encoder.encode(
                decoded.document,
                project_attachment(decoded.document),
                decoded.source_info,
            )
            rows = [
                json.loads(line)
                for artifact in bundle.files
                if artifact.name == "search_units.jsonl"
                for line in artifact.content.splitlines()
            ]
        elif entrypoint == "publisher_materialize":
            result = publisher.publish(decoder.decode(source), source)
            async with runtime.acquire() as snapshot:
                evidence = await snapshot.evidence_reader.search(
                    SearchCriteria(
                        source=DetectionSource.LOGIC,
                        section_codes=(
                            SearchSectionCode("27"),
                            SearchSectionCode("10.1"),
                        ),
                    ),
                    (
                        ResolvedMedicine(
                            medicine=DomainMedicineMatch("", (), ("111111111111",), ()),
                            document_ids=("000001_test",),
                        ),
                    ),
                )
            assert {row.section["code"] for row in evidence} == {"27", "10.1"}
            combined = "".join(row.excerpt for row in evidence)
            assert "追補の原文本文" in combined and "相手薬の原文" in combined
            assert all(
                row.unit_id.value.startswith(
                    f"000001_test:{hashlib.sha256(source).hexdigest()}:"
                )
                for row in evidence
            )
            rows = _saved_rows(
                store, result.document_id, result.source_sha256, result.generation_id
            )
        else:
            assert app is not None
            async with (
                app.router.lifespan_context(app),
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://test"
                ) as client,
            ):
                response = await client.post(
                    "/api/attachment-imports",
                    files={"file": ("source.xml", source, "application/xml")},
                )
                assert response.status_code == 201, response.text
                async with app.state.generation_runtime.acquire() as snapshot:
                    evidence = await snapshot.evidence_reader.search(
                        SearchCriteria(
                            source=DetectionSource.LOGIC,
                            section_codes=(
                                SearchSectionCode("27"),
                                SearchSectionCode("10.1"),
                            ),
                        ),
                        (
                            ResolvedMedicine(
                                medicine=DomainMedicineMatch(
                                    "", (), ("111111111111",), ()
                                ),
                                document_ids=("000001_test",),
                            ),
                        ),
                    )
                    assert {row.section["code"] for row in evidence} == {"27", "10.1"}
                    combined = "".join(row.excerpt for row in evidence)
                    assert "追補の原文本文" in combined
                    assert "相手薬の原文" in combined
                    assert all(
                        row.unit_id.value.startswith(
                            f"000001_test:{hashlib.sha256(source).hexdigest()}:"
                        )
                        for row in evidence
                    )
                payload = response.json()
                rows = _saved_rows(
                    store,
                    payload["document_id"],
                    payload["source_sha256"],
                    payload["generation_id"],
                )
        by_code = {row["section"]["code"]: row for row in rows}
        assert by_code["27"]["section"]["title"] == "追加項目の正式名称"
        assert "追補の原文本文" in by_code["27"]["text"]
        assert "注入薬剤列" in by_code["10.1"]["text"]
        assert "相手薬の原文" in by_code["10.1"]["text"]
        assert by_code["27"]["document_key"] == "000001_test"
        assert by_code["10.1"]["document_key"] == "000001_test"
        assert by_code["27"]["unit_id"] == "000001_test:27"
        assert by_code["10.1"]["unit_id"] == "000001_test:10.1"
        assert by_code["27"]["kind"] == "section"
        assert by_code["10.1"]["kind"] == "section"
    finally:
        await workers.aclose()


def _saved_rows(store, document_id, digest, generation_id):
    target = store._target(DocumentId(document_id), digest)
    assert hashlib.sha256((target / "source.xml").read_bytes()).hexdigest() == digest
    assert (
        json.loads((target / "document.json").read_bytes())["source"]["sha256"]
        == digest
    )
    version_id = f"{document_id}:{digest}"
    generation_file = (
        store.root
        / "generations"
        / generation_id
        / (hashlib.sha256(version_id.encode()).hexdigest() + ".jsonl")
    )
    generation_rows = [
        json.loads(line)
        for line in generation_file.read_text(encoding="utf-8").splitlines()
    ]
    by_code = {row["section"]["code"]: row for row in generation_rows}
    assert set(by_code) == {"27", "10.1"}
    for code, row in by_code.items():
        assert row["schema_version"] == "medi-chat.pmda-sections.v3"
        assert row["document_key"] == document_id
        assert row["source_sha256"] == digest
        assert row["unit_id"] == f"{version_id}:{code}"
    assert by_code["10.1"]["blocks"][0]["columns"][0] == "注入薬剤列"
    assert by_code["10.1"]["blocks"][0]["rows"][0][0]["text"] == "相手薬の原文"
    return [
        json.loads(line)
        for line in (target / "search_units.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]


@pytest.mark.asyncio
async def test_tc21_injected_heading_policy_reaches_old_lease_and_new_request(
    tmp_path, monkeypatch
):
    definitions = loader.get_package_insert_definitions()
    policy = replace(
        definitions.text_search_policy, scope_heading_texts=frozenset({"特別見出し"})
    )
    structured = tmp_path / "structured"
    structured.mkdir()
    index = tmp_path / "index.sqlite3"
    _migrate_database(index, structured)
    store = FileAttachmentImportStore(tmp_path / "imports")
    publisher = SqliteRegistrationPublisher(
        index, store, xml_settings=definitions.xml_settings
    )
    decoder = PmdaXmlDecoder(xml_settings=definitions.xml_settings)
    old = xml_source(
        "<Warnings><Detail><Lang>特別見出し</Lang></Detail></Warnings><ContraIndications><Detail><Lang>旧保持原文</Lang></Detail></ContraIndications>"
    )
    new = xml_source(
        "<Warnings><Detail><Lang>特別見出し</Lang></Detail></Warnings><ContraIndications><Detail><Lang>新保持原文</Lang></Detail></ContraIndications>"
    ).replace(b"2026-10", b"2026-11")
    first = publisher.publish(decoder.decode(old), old)
    workers = ReadWorkers()
    runtime = GenerationRuntime(
        publisher,
        workers=workers,
        text_search_policy=policy,
        xml_settings=definitions.xml_settings,
    )
    from backend.infrastructure.persistence import generation_runtime

    real_heading_judgment = generation_runtime.is_scope_heading_only
    judgments = []

    def observe_heading(unit, *, text_search_policy):
        result = real_heading_judgment(unit, text_search_policy=text_search_policy)
        judgments.append((unit["unit_id"], unit["kind"], text_search_policy, result))
        return result

    monkeypatch.setattr(generation_runtime, "is_scope_heading_only", observe_heading)

    def forbid(*args, **kwargs):
        pytest.fail("injected runtime policy returned to definition source")

    for name in (
        "backend.infrastructure.package_insert_definitions.loader",
        "backend.infrastructure.persistence.generation_runtime",
        "backend.infrastructure.persistence.registration_publisher",
        "backend.infrastructure.pmda_xml.decoder",
        "backend.infrastructure.pmda_xml.units",
        "backend.infrastructure.pmda_xml.sections",
        "backend.infrastructure.pmda_xml.xml_nodes",
        "backend.infrastructure.pmda_xml.artifacts",
    ):
        monkeypatch.setattr(
            import_module(name), "get_package_insert_definitions", forbid, raising=False
        )
    monkeypatch.setattr(loader, "load_package_insert_definitions", forbid)
    criteria = SearchCriteria(
        source=DetectionSource.LOGIC,
        section_codes=(SearchSectionCode("1"), SearchSectionCode("2")),
    )
    target = (
        ResolvedMedicine(
            medicine=DomainMedicineMatch("", (), ("111111111111",), ()),
            document_ids=("000001_test",),
        ),
    )
    try:
        async with runtime.acquire() as old_snapshot:
            latest = publisher.publish(decoder.decode(new), new)
            assert old_snapshot.generation_id.value == first.generation_id
            old_rows = await old_snapshot.evidence_reader.search(criteria, target)
            assert [row.section["code"] for row in old_rows] == ["1", "2"]
            assert [row.excerpt for row in old_rows] == [
                "<p>特別見出し</p>",
                "<p>旧保持原文</p>",
            ]
            assert [row.unit_id.value for row in old_rows] == [
                f"000001_test:{hashlib.sha256(old).hexdigest()}:{code}"
                for code in ("1", "2")
            ]
            async with runtime.acquire() as new_snapshot:
                assert new_snapshot.generation_id.value == latest.generation_id
                new_rows = await new_snapshot.evidence_reader.search(criteria, target)
                assert [row.section["code"] for row in new_rows] == ["1", "2"]
                assert [row.excerpt for row in new_rows] == [
                    "<p>特別見出し</p>",
                    "<p>新保持原文</p>",
                ]
                assert [row.unit_id.value for row in new_rows] == [
                    f"000001_test:{hashlib.sha256(new).hexdigest()}:{code}"
                    for code in ("1", "2")
                ]
        assert policy is not definitions.text_search_policy
        assert (
            policy.scope_heading_texts
            != definitions.text_search_policy.scope_heading_texts
        )
        assert {unit_id for unit_id, _, _, _ in judgments} == {
            row.unit_id.value for row in old_rows + new_rows
        }
        assert all(
            kind == "section" and observed_policy is policy and result is False
            for _, kind, observed_policy, result in judgments
        )
        assert [row.excerpt for row in old_rows] == [
            "<p>特別見出し</p>",
            "<p>旧保持原文</p>",
        ]
        with pytest.raises(RuntimeError, match="released"):
            await old_snapshot.evidence_reader.search(criteria, target)
        with sqlite3.connect(index) as connection:
            assert connection.execute(
                "SELECT count(*) FROM generation_leases"
            ).fetchone() == (0,)
    finally:
        await workers.aclose()
