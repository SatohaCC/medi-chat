# 開発ツールとスクリプト

テスト本体とlint・型検査設定は`backend/`・`frontend/`が所有する。`scripts/`にはアーキテクチャ検査、PostgreSQL初期化、環境解決、デプロイ用要件生成、開発ログ設定を置く。

| 場所 | 責務 |
| --- | --- |
| `checks/*_architecture.py` | Layer・Domain・Application・Infrastructureの静的構造検査 |
| `postgres/` | PostgreSQLの初期化 |
| `export-vercel-requirements.mjs` | `backend/uv.lock`からVercel用`requirements.txt`を生成・検証 |
| `root-environment.cjs` | ルート`.env.local`の読込補助 |
| `uvicorn-dev-logging.json` | 開発サーバーのアクセスログ設定 |

## 開発バックエンドのログ

`pnpm dev:backend`は`uvicorn --reload`を直接起動し、stdout/stderrをコンソールへ表示する。アクセスログのクエリは`uvicorn-dev-logging.json`のフィルタで`?[REDACTED]`へ伏せる。ログ本文や例外の内容を共有する前に確認し、患者情報を含む原文を外部へ貼り付けない。

ログはコンソールへ出力し、セッションログのファイル保存・自動再起動・稼働ログ検査は持たない。`pnpm dev`で別起動するfrontendのログは対象外。
