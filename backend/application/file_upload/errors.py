"""原本の転送・一時保存に固有の失敗。"""


class FileUploadError(Exception):
    def __init__(self, code: str, message: str, *, phase: str = "upload") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.phase = phase


class UploadConflict(FileUploadError):
    pass


class UploadGone(FileUploadError):
    pass


class UploadLimitExceeded(FileUploadError):
    pass


class UploadStorageError(FileUploadError):
    pass


class InvalidUpload(FileUploadError):
    pass
