"""全登録入口で共用する、indexに結び付いたOS lock。"""

import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from ...application.attachment_import.import_errors import ImportStorageError
from .attachment_import_store import FileAttachmentImportStore


@contextmanager
def registration_lock(
    index_path: Path, check_cancel: Callable[[], None] = lambda: None
) -> Iterator[None]:
    path = index_path.resolve().with_name("." + index_path.name + ".publisher.lock")
    if path.is_symlink():
        raise ImportStorageError(
            "publisher_lock_unsafe", "Publisher lock is unsafe", phase="publication"
        )
    with path.open("a+b") as stream:
        if stream.seek(0, 2) == 0:
            stream.write(b"0")
            stream.flush()
        while True:
            check_cancel()
            try:
                FileAttachmentImportStore._file_lock(stream, unlock=False)
                break
            except OSError:
                time.sleep(0.01)
        try:
            yield
        finally:
            FileAttachmentImportStore._file_lock(stream, unlock=True)
