"""配置に依存しないテスト用の共有パス。"""

from pathlib import Path

TEST_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = TEST_ROOT.parent
PROJECT_ROOT = BACKEND_ROOT.parent
FIXTURES_ROOT = TEST_ROOT / "fixtures"
