"""受信済み原本を整合性確認済みとして取り出す。文書の登録はしない。"""

from backend.application.file_upload.commands.models import UploadedSource
from backend.application.file_upload.interfaces.temporary_file_store import (
    TemporaryFileStore,
)


def complete_upload(upload_id: str, *, store: TemporaryFileStore) -> UploadedSource:
    return store.read(upload_id)
