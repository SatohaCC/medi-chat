"""他コンテキストから参照できる添付文書の公開ID。"""

from dataclasses import dataclass

from ..foundation.primitives.identifiers import EntityStringId


@dataclass(frozen=True, slots=True)
class DocumentId(EntityStringId):
    """添付文書を識別するID。"""


@dataclass(frozen=True, slots=True)
class DocumentVersionId(EntityStringId):
    """文書IDとは別の、文書と実原本SHAを組にした版ID。"""


@dataclass(frozen=True, slots=True)
class ArtifactFileId(EntityStringId):
    """登録台帳が所有する具体的なファイルの識別子。パスではない。"""
