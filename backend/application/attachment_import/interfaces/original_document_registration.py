"""原本から登録結果を得る境界。XML・DBの中間表現は公開しない。"""

from collections.abc import Callable
from typing import Protocol

from backend.application.attachment_import.commands.models import ImportResult


class OriginalDocumentRegistration(Protocol):
    def register(
        self, source: bytes, *, original_filename: str, check_cancel: Callable[[], None]
    ) -> ImportResult: ...
