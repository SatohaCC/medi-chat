"""索引構築で扱う意味のある失敗。"""


class IndexSourceError(RuntimeError):
    """索引構築に使う外部ソースを読み取れない、または内容が不正。"""
