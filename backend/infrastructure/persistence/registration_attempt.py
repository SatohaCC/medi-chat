"""Private concrete ownership journal; never a public generation pointer."""

import hashlib
import json
import os
import re
import uuid
from pathlib import Path

from ...application.attachment_import.import_errors import ImportStorageError
from .process_identity import process_identity


class RegistrationAttempt:
    def __init__(self, root: Path):
        self.root = root
        directory = root / ".registration-attempts"
        if directory.is_symlink() or not directory.resolve().is_relative_to(root):
            raise ImportStorageError(
                "unsafe_owned_file",
                "Private ownership journal is unsafe",
                phase="artifact",
            )
        directory.mkdir(exist_ok=True)
        self.path = directory / (uuid.uuid4().hex + ".json")
        self.files: dict[str, str] = {}
        self.owner = process_identity(os.getpid())
        self.finished = False

    def claim(self, path: Path, content: bytes) -> None:
        self.files[str(path)] = hashlib.sha256(content).hexdigest()
        self.save()

    def save(self) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {
                    "owner_pid": os.getpid(),
                    "owner_start": self.owner,
                    "finished": self.finished,
                    "files": self.files,
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def finish(self) -> None:
        if self.path.exists():
            self.finished = True
            self.save()

    @staticmethod
    def recover(root: Path, referenced: set[str]) -> None:
        directory = root / ".registration-attempts"
        if directory.is_symlink():
            return
        for journal in directory.glob("*.json"):
            if journal.is_symlink():
                continue
            try:
                value = json.loads(journal.read_bytes())
                if (
                    not value["finished"]
                    and process_identity(value["owner_pid"]) == value["owner_start"]
                ):
                    continue
                complete = True
                for raw, digest in value["files"].items():
                    path = Path(raw)
                    if raw in referenced:
                        continue
                    relative = path.relative_to(root)
                    parts = relative.parts
                    known = (
                        len(parts) == 4
                        and parts[0] == "versions"
                        and re.fullmatch(r"[0-9a-f]{64}", parts[1])
                        and re.fullmatch(r"[0-9a-f]{64}", parts[2])
                        and parts[3]
                        in {
                            "source.xml",
                            "document.json",
                            "search_units.jsonl",
                            "validation.json",
                            "source_metadata.json",
                            "result.json",
                            "integrity.json",
                            ".attachment-stage",
                        }
                    ) or (
                        len(parts) == 3
                        and parts[0] == "generations"
                        and re.fullmatch(r"[0-9a-f]{32}", parts[1])
                        and re.fullmatch(r"[0-9a-f]{64}\.jsonl", parts[2])
                    )
                    if (
                        not known
                        or any(
                            parent.is_symlink()
                            for parent in (path, *path.parents)
                            if parent.is_relative_to(root)
                        )
                        or not path.resolve().is_relative_to(root)
                    ):
                        complete = False
                        continue
                    if not path.exists():
                        continue
                    if (
                        not path.is_file()
                        or hashlib.sha256(path.read_bytes()).hexdigest() != digest
                    ):
                        complete = False
                        continue
                    path.unlink()
                if complete:
                    journal.unlink()
            except (OSError, ValueError, TypeError, KeyError):
                # Unknown owner/path/content is preserved, never guessed or aged out.
                continue
