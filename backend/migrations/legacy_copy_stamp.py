"""検証した旧索引の専用stamp経路。通常の未管理DB拒否と区別する。"""

from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from ..infrastructure.persistence.legacy_content_validator import (
    validate_legacy_content,
)
from ..infrastructure.persistence.legacy_schema_validator import validate_legacy_schema

LEGACY_REVISION = "0001_v3_schema"
STAMP_COPY_ATTRIBUTE = "validated_legacy_copy_stamp"


@dataclass(frozen=True)
class LegacyCopyStamp:
    index_path: Path


def validate_stamp_copy(approval: LegacyCopyStamp, index_path: Path) -> None:
    if approval.index_path != index_path.resolve():
        raise ValueError("Legacy stamp permission does not match the output index")
    validate_legacy_schema(index_path)
    validate_legacy_content(index_path)


def stamp_and_upgrade_legacy_copy(index_path: Path) -> str:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.cmd_opts = Namespace(x=[f"index_path={index_path.resolve()}"])
    head = ScriptDirectory.from_config(config).get_current_head()
    if head is None:
        raise ValueError("Legacy migration has no target revision")
    approval = LegacyCopyStamp(index_path.resolve())
    validate_stamp_copy(approval, index_path)
    config.attributes[STAMP_COPY_ATTRIBUTE] = approval
    try:
        command.stamp(config, LEGACY_REVISION)
    finally:
        config.attributes.pop(STAMP_COPY_ATTRIBUTE, None)
    command.upgrade(config, "head")
    return head
