# medi-chat

PMDAの電子添文を検索し、原文・出典・改訂情報を確認しながら質問できる、薬剤師向けの対話システムです。
Next.js、FastAPI、PostgreSQLを使用しています。

## 主な機能

- 医薬品名・YJコードから対象を選択
- 項目・キーワード・AIの意図判定による添付文書検索
- 出典付きの根拠表示と回答のストリーミング
- PMDA XMLの取り込みと改訂年月に基づく公開版の管理

## 開発を始める

Node.js・pnpm、Python 3.14以上・uv、Docker Desktopが必要です。コマンドはリポジトリルートで実行します。

```bash
pnpm install --frozen-lockfile
uv sync --project backend --locked --group dev
```

[ローカル開発手順](docs/development/local-development.md)に従って環境変数・PostgreSQL・原本データを準備した後、起動します。

```bash
pnpm dev
```

フロントエンド: http://localhost:3000 ／ バックエンド: http://localhost:8000

## 構成

| 場所 | 内容 |
| --- | --- |
| `frontend/` | チャット・添付文書取り込みの画面 |
| `backend/` | API・ユースケース・Domain・外部サービス連携 |
| `data/pmda/` | PMDA原本とオフライン変換用データ |
| `docs/` | 開発・設計・運用の資料 |

## 主なコマンド

| コマンド | 内容 |
| --- | --- |
| `pnpm dev` | frontend・backendの起動 |
| `pnpm lint` | lint・依存関係の検査 |
| `pnpm typecheck` | TypeScript・Pythonの型検査 |
| `pnpm test:backend` | backendのテスト（実DBテストには接続設定が必要） |
| `pnpm test:e2e` | ブラウザテスト（DB・原本データの準備が必要） |
| `pnpm build` | frontendのビルド |

## ドキュメント

- [ローカル開発・DBの準備](docs/development/local-development.md)
- [バックエンドの概要](backend/README.md)
- [バックエンドの設計・依存ルール](docs/architecture/backend-design.md)
- [添付文書の取り込み・登録](docs/development/attachment-import.md)
- [PMDAデータの作業案内](data/pmda/README.md)
- [共通定義の編集方法](backend/infrastructure/package_insert_definitions/README.md)
- [デプロイ手順](docs/development/vercel-deployment.md)
- [機能一覧](docs/feature-list.md)
- [エージェント向け資料](.agents/README.md)
