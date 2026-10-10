"""データツールの作業ディレクトリに依存しないパス解決。"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve_project_path(path: Path) -> Path:
    """相対パスをプロジェクトルート基準で解決する。"""
    return (PROJECT_ROOT / path).resolve()
