"""技術非依存の索引構築処理。"""

from .index_contracts import IndexSourceReader, IndexWriter
from .index_models import IndexBuildResult


def build_index(
    source_reader: IndexSourceReader, writer: IndexWriter
) -> IndexBuildResult:
    snapshot = source_reader.read_snapshot()
    return writer.replace(snapshot)
