"""添付文書の原本改訂年月に基づく選択規則。"""

from .exceptions import ConflictingRevisionError
from .value_objects import RegistrationVersion


def latest_attachment(
    current: RegistrationVersion | None, candidate: RegistrationVersion
) -> RegistrationVersion:
    """登録順を使わず新しい原本を選ぶ。同年月の別原本は曖昧として拒否する。"""
    if current is None or candidate.revised_at.value > current.revised_at.value:
        return candidate
    if candidate.version_id == current.version_id:
        return current
    if candidate.revised_at == current.revised_at:
        raise ConflictingRevisionError(
            "different originals have the same revision month"
        )
    return current
