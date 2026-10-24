from backend.application.file_upload.interfaces.temporary_file_store import (
    TemporaryFileStore,
)


def upload_part(
    upload_id: str, index: int, content: bytes, *, store: TemporaryFileStore
) -> None:
    store.put(upload_id, index, content)
