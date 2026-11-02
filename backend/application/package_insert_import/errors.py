"""取り込み境界の失敗。HTTPへの変換はPresentationが担当する。"""


class PackageInsertImportError(Exception):
    def __init__(self, code: str, message: str, *, phase: str = "validation") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.phase = phase
        self.conflicts: tuple[tuple[str, tuple[str, ...]], ...] = ()


class InvalidPackageInsert(PackageInsertImportError):
    pass


class UnsupportedPackageInsert(PackageInsertImportError):
    pass


class ImportLimitExceeded(PackageInsertImportError):
    pass


class ImportConflict(PackageInsertImportError):
    pass


class ImportStorageError(PackageInsertImportError):
    pass


class ImportNotFound(PackageInsertImportError):
    pass


class ImportGone(PackageInsertImportError):
    pass


class ImportCancelled(Exception):
    pass
