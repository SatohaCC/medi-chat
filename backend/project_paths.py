"""作業ディレクトリに依存しないバックエンドとリポジトリの基準パス。"""

from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
