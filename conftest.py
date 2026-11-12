"""Global pytest configuration for Windows / DSH sandbox compatibility."""

import sys
from contextlib import suppress
from pathlib import Path

import _pytest.pathlib
import _pytest.tmpdir
import pytest

_patches = pytest.MonkeyPatch()
_orig_cleanup = _pytest.pathlib.cleanup_dead_symlinks


def _safe_cleanup(root: Path) -> None:
    with suppress(OSError):
        _orig_cleanup(root)


_patches.setattr(_pytest.pathlib, "cleanup_dead_symlinks", _safe_cleanup)
_patches.setattr(_pytest.tmpdir, "cleanup_dead_symlinks", _safe_cleanup)

if sys.platform == "win32":
    # mode=0o700 strips inherited container ACLs in restricted Windows sandboxes.
    _patches.setattr(_pytest.tmpdir, "get_user", lambda: "dsh_worker")
    _orig_mkdir = Path.mkdir

    def _safe_mkdir(
        self: Path, mode: int = 0o777, parents: bool = False, exist_ok: bool = False
    ) -> None:
        _orig_mkdir(self, mode=0o777, parents=parents, exist_ok=exist_ok)

    _patches.setattr(Path, "mkdir", _safe_mkdir)


def pytest_unconfigure() -> None:
    _patches.undo()
