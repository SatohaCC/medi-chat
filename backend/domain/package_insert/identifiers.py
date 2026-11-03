"""他コンテキストから参照できる添付文書の公開ID。"""

from dataclasses import dataclass

from ..foundation.primitives.identifiers import EntityStringId


@dataclass(frozen=True, slots=True)
class DocumentId(EntityStringId):
    """添付文書を識別するID。"""
