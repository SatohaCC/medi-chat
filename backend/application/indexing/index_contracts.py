"""索引ソースと書込みの技術非依存契約。"""

from typing import Protocol

from .index_models import IndexBuildResult, SourceSnapshot


class IndexSourceReader(Protocol):
    def read_snapshot(self) -> SourceSnapshot: ...


class IndexWriter(Protocol):
    def replace(self, snapshot: SourceSnapshot) -> IndexBuildResult: ...
