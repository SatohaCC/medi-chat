import pytest
from backend.application.attachment_import.import_errors import ImportStorageError
from backend.infrastructure.persistence.registration_attempt import RegistrationAttempt
from backend.tests.test_registration_publisher import publish, snapshot, source
from backend.tests.test_registration_publisher import publisher as publisher


def test_tc097_private_journal_io_failure_has_artifact_phase_and_no_publication(
    publisher, monkeypatch
):
    publish(publisher, source("既存公開本文"))
    before = snapshot(publisher)

    def fail(*args, **kwargs):
        raise OSError("controlled private journal allocation failure")

    monkeypatch.setattr(RegistrationAttempt, "__init__", fail)
    with pytest.raises(ImportStorageError) as caught:
        publish(publisher, source("公開不可本文"))
    assert caught.value.phase == "artifact"
    assert snapshot(publisher) == before


def test_tc098_published_receipt_is_not_masked_by_journal_finalization_failure(
    publisher, monkeypatch
):
    publish(publisher, source("旧本文"))

    def fail(*args, **kwargs):
        raise OSError("controlled private journal finalization failure")

    monkeypatch.setattr(RegistrationAttempt, "finish", fail)
    registered = publish(publisher, source("新公開本文"))
    assert registered.status == "registered"
    assert (
        publisher.read_result(
            registered.document_id, registered.source_sha256
        ).generation_id
        == registered.generation_id
    )
