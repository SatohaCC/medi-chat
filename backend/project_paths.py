"""作業ディレクトリに依存しないバックエンドとリポジトリの基準パス。"""

from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent


def resolve_project_path(path: Path) -> Path:
    """相対パスをプロジェクトルート基準で解決する。"""
    return (PROJECT_ROOT / path).resolve()
