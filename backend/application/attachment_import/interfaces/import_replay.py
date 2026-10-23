"""Replay a completed command without registering the source again."""

from typing import Protocol

from backend.application.attachment_import.commands.models import ImportResult


class ImportReplay(Protocol):
    def replay_result(self, document_id: str, digest: str) -> ImportResult: ...
