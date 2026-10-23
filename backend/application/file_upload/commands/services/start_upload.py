from collections.abc import Callable

from backend.application.file_upload.commands.models import UploadSpec
from backend.application.file_upload.interfaces.temporary_file_store import (
    TemporaryFileStore,
)


def start_upload(
    spec: UploadSpec, *, store: TemporaryFileStore, check_cancel: Callable[[], None]
) -> str:
    check_cancel()
    return store.create(spec)
