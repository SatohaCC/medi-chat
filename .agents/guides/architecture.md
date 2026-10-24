# 設計と契約

- 全体構成は[README](../../README.md)、バックエンドの責務・依存・命名は[バックエンド設計](../../docs/architecture/backend-design.md)の関連節を参照する。既存の図や詳細をここへ複製しない。
- READMEと現在のコード・差分を照合する。進行中の配置変更や未承認の提案を、確定した設計として扱わない。
- 公開APIのJSON項目、REST/WebSocketのイベント、LLMへ渡す会話・根拠、CLI/module起動の契約に影響する変更を計画で明示する。
- 共通の添付文書定義は[Infrastructure定義README](../../backend/infrastructure/package_insert_definitions/README.md)に従う。検索・Jev・プロンプト・XML変換で別々の対応表を追加しない。
- レイヤー間・レイヤー内の依存境界は[backend/pyproject.toml](../../backend/pyproject.toml)のImport Linter（24契約）と`backend/tests/architecture/test_architecture_dependencies.py`で機械的に検査する。`Presentation -> Domain`の完全禁止など例外（`ignore_imports`）を増やさない厳格なルールを維持し、`pnpm --filter backend lint`で即座に検証する。
- モジュール移動や再公開の削除では利用側・テスト・CLI・起動点を確認し、必要な検証を計画する。ファイル移動や構文確認だけでは実行時の互換性を確認したことにしない。

- Applicationの配置・公開範囲・絶対importは[Applicationハーネス](../../docs/architecture/application-architecture.md)の規則と移行状況を参照する。import段階の成功と全規則への適合を区別する。
- Domainの配置・依存・公開ID・不変性は[Domainハーネス](../../docs/architecture/domain-architecture.md)で強制する。新規コンテキストにも自動適用し、構造検査と業務上の不変条件のテストを区別する。
