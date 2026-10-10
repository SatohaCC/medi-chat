"""構造化添付文書や検索索引を利用できない場合の例外。"""


class PackageInsertStoreError(RuntimeError):
    """添付文書の元データが不足しているか、索引を構築できない。"""
