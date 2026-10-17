---
name: ddd-onion-bestpractices
description: FastAPIを含むバックエンドのドメイン駆動設計とオニオンアーキテクチャのベストプラクティスを確認・適用するときに使う。
---

# DDD & Onion Architecture Core Rules

## 1. レイヤー定義・依存方向
依存方向は常に **外層 $\rightarrow$ 内層**（内層は外層の詳細に非依存）。

| レイヤー | 責務 | 依存制約（Import Linterで機械強制） | 詳細 |
| :--- | :--- | :--- | :--- |
| **Domain** | ビジネスルール・概念・状態の整合性 | 最内層。外部ライブラリ・DB・FW・外層に一切非依存 | [Domain](references/domain-layer.md) |
| **Application** | ユースケースの調整（オーケストレーション） | `Domain` のみに依存。ビジネスロジックは持たない | [App](references/application-layer.md) |
| **Infrastructure** | 技術詳細（DB, API, 外部連携）の実装・DI配線 | `Application`・`Domain`・`Config` に依存（上位層のInterfaceを具象実装） | [Infra](references/infrastructure-layer.md) |
| **Presentation** | 外部入出力（REST/WS, DTO変換, `Depends`） | **`Application`（と `Config`）のみに依存**。`Domain`・`Infrastructure` への依存は完全禁止 | [Presentation](references/presentation-layer.md) |

## 2. リンターによるルール強制と実装効率化（重要）
- **例外（`ignore_imports`）を作らない厳格でシンプルなルール**:
  - 「PresentationからDomainの一部だけ許可」のような例外運用は、リンターが間接推移依存（`Presentation -> Domain -> Domain内部`）まで遮断する性質上、例外リストの肥大化や実装時の判断コスト増大を招く。
  - レイヤー間（例：`Presentation does not depend on domain`）は **例外ゼロの完全禁止** とし、境界での型公開やドメイン例外の変換は `Application` 層で完結させる。
- **レイヤー内部の階層・独立性もリンターで機械化**:
  - **Domain内**: コンテキスト間の独立（公開ID `identifiers.py` のみ越境可）および `identifiers -> exceptions -> primitives -> value_objects -> entities -> repositories -> services` の単方向階層。
  - **Application内**: コンテキスト間の有向パイプライン境界（`chat -> retrieval -> medicine`、`attachment_import -> indexing -> medicine`）。
  - **Presentation内**: `routes -> dependencies -> adapter service -> dto mappers -> dto models` の5段階単方向階層。
  - **Infrastructure内**: 外部技術アダプター（`llm` / `intent` / `morphology` / `pmda_xml`）間の相互独立、`persistence -> sources` 禁止、`package_insert_definitions` から他アダプターへの依存禁止、共通payloadマッパー（`index_payloads.py` / `evidence_mapping.py`）からアダプターへの依存禁止。
- **Ruff + Import Linter + ASTテストによる即時フィードバック**:
  - 実装・リファクタリング時は人間の目視レビューに頼らず、`pnpm --filter backend lint`（Ruff + Import Linter全24契約）と `test_architecture_dependencies.py` を実行して機械的に境界適合を確認する。

## 3. 核心原則
- **IDの命名**: 識別子の型名は `〜Id`、属性名は `〜_id` / `〜_ids` に統一する。既存の保存形式との互換性が必要なら外側の境界で変換する。[詳細](references/domain-layer.md)
- **原本と利用側の責務**: 原本の構造・整合性と、検索・表示用の派生モデルを責務で分ける。元データが同じという理由だけで同じコンテキストに置かない。[詳細](references/domain-layer.md)
- **公開IDの境界（1コンテキスト＝1公開ID）**: Domain/Applicationの他コンテキストから直接参照できるのは、各コンテキストの `identifiers.py` に定義した1つの公開ID Primitive（`attachment: DocumentId`, `medicine: YjCode`, `retrieval: SearchUnitId`）だけとする。共有識別語彙はshared、共通基底はfoundationに置く。[詳細](references/domain-layer.md)
- **操作の提供方法を統一する**: 保守性のため、同じ目的・同じ契約の操作は1つの方法で提供する。同等のラッパー、別名API、迂回経路を追加しない。新しい提供方法が必要な場合は既存の方法を置き換え、利用側とテストを移行する。目的や契約が異なる操作は、それぞれの責務を明示する。
- **直接生成**: Entity / Value Object は型付け済みの値を渡してコンストラクタで生成する。引数変換だけの `create()` は定義しない。Primitiveの正規化・単一値検証と、モデルの組み合わせの不変条件を分担する。[詳細](references/domain-layer.md)
- **暗黙の変換を避ける**: モデルの `__post_init__()` で基本型をPrimitiveや不変コレクションへ変換しない。単一値の検証・整形はPrimitiveが所有し、利用側はその生成結果を渡す。原文を保持する値は、その契約に応じて正規化と空値の扱いを定義する。
- **依存性逆転 (DIP) と2段階DI**: 上位層は抽象（Interface/Protocol）に依存し、起動時の具象生成・配線は `infrastructure/composition/app_lifespan.py`（Composition Root）、リクエスト単位の注入は `presentation/dependencies.py`（FastAPI `Depends`）に集約する。[詳細](references/dependency-inversion-principle.md)
- **データフロー**: `Presentation (Router -> Depends -> DTO Adapter)` $\rightarrow$ `Application (Application Service -> Use Case)` $\rightarrow$ `Domain` / `Repository Interface` (具象実行は `Infrastructure`)
- **Domainの標準配置**: 各コンテキストは `identifiers.py`、`primitives.py`、`value_objects.py`、`entities.py`、`repositories.py`、`services.py`、`exceptions.py` の直下モジュールに分ける。責務別ディレクトリや互換用Facadeは増やさない。[詳細](references/domain-layer.md)
- **トランザクション (UoW)**: `Application` 層または注入された Publisher ポート境界で整合性を制御する。[詳細](references/unit-of-work.md)
