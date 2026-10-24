# Backend

FastAPIで医薬品の検索、添付文書の登録、根拠付きチャットを提供します。
Python依存はuvで管理し、保存先にはPostgreSQLを使用します。

## 構成

| ディレクトリ | 責務 |
| --- | --- |
| `presentation/` | REST・WebSocket、Pydantic DTO、Applicationとの変換 |
| `application/` | チャット、検索、索引投影、登録のユースケースとポート |
| `domain/` | 医薬品・添付文書の概念と不変条件 |
| `infrastructure/` | PostgreSQL・XML・外部AI・CLI・DI配線 |
| `config/` | 環境設定 |
| `tests/` | 各層・統合・アーキテクチャの検証 |

検索条件・意図判定・根拠の統合は `application/retrieval`、索引用モデルは `application/indexing` が所有します。
Domainは外側の層に依存せず、PresentationはApplicationを通して処理を呼び出します。

## 開発コマンド

リポジトリルートから実行します。環境設定とDBの準備は[ローカル開発](../docs/development/local-development.md)を参照してください。

```bash
pnpm dev:backend
pnpm --filter backend lint
pnpm typecheck:python
pnpm test:backend
```

## 詳細資料

- [設計・依存方向・型とモデルの方針](../docs/architecture/backend-design.md)
- [DB運用・マイグレーション](../docs/architecture/backend-design.md#データベース運用とマイグレーション)
- [添付文書の取り込み・登録](../docs/development/attachment-import.md)
- [共通定義の編集方法](infrastructure/package_insert_definitions/README.md)
- [テストと検証](../docs/development/local-development.md#検証)
