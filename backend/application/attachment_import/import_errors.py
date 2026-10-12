"""取り込み境界の失敗。HTTPへの変換はPresentationが担当する。"""


class AttachmentImportError(Exception):
    def __init__(self, code: str, message: str, *, phase: str = "validation") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.phase = phase
        self.conflicts: tuple[tuple[str, tuple[str, ...]], ...] = ()


class InvalidAttachment(AttachmentImportError):
    pass


class UnsupportedAttachment(AttachmentImportError):
    pass


class ImportLimitExceeded(AttachmentImportError):
    pass


class ImportConflict(AttachmentImportError):
    pass


class ImportStorageError(AttachmentImportError):
    pass


class ImportNotFound(AttachmentImportError):
    pass


class ImportGone(AttachmentImportError):
    pass


class ImportCancelled(Exception):
    pass
