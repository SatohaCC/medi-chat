---
name: ddd-onion-bestpractices
description: FastAPIを含むバックエンドのドメイン駆動設計とオニオンアーキテクチャのベストプラクティスを確認・適用するときに使う。
---

# DDD & Onion Architecture Core Rules

## 1. レイヤー定義・依存方向
依存方向は常に **外層 $\rightarrow$ 内層**（内層は外層の詳細に非依存）。

| レイヤー | 責務 | 依存制約 | 詳細 |
| :--- | :--- | :--- | :--- |
| **Domain** | ビジネスルール・概念・状態の整合性 | 最内層。外部ライブラリ・DB・FWに非依存 | [Domain](references/domain-layer.md) |
| **Application** | ユースケースの調整（オーケストレーション） | Domainに依存。ビジネスロジックは持たない | [App](references/application-layer.md) |
| **Infrastructure** | 技術詳細（DB, API, 外部連携）の実装 | 上位層の抽象（Interface）を具象実装 | [Infra](references/infrastructure-layer.md) |
| **Presentation** | 外部入出力（Web/API/UI, バリデーション） | App層のみ呼び出し。DB直接操作・ロジック保持禁止 | [Presentation](references/presentation-layer.md) |

## 2. 核心原則
- **IDの命名**: 識別子の型名は `〜Id`、属性名は `〜_id` / `〜_ids` に統一する。既存の保存形式との互換性が必要なら外側の境界で変換する。[詳細](references/domain-layer.md)
- **原本と利用側の責務**: 原本の構造・整合性と、検索・表示用の派生モデルを責務で分ける。元データが同じという理由だけで同じコンテキストに置かない。[詳細](references/domain-layer.md)
- **公開IDの境界**: 他コンテキストから直接参照できるのは `identifiers.py` に定義したID Primitiveだけとする。共有識別語彙はshared、共通基底はfoundationに置く。[詳細](references/domain-layer.md)
- **操作の提供方法を統一する**: 保守性のため、同じ目的・同じ契約の操作は1つの方法で提供する。同等のラッパー、別名API、迂回経路を追加しない。新しい提供方法が必要な場合は既存の方法を置き換え、利用側とテストを移行する。目的や契約が異なる操作は、それぞれの責務を明示する。
- **直接生成**: Entity / Value Object は型付け済みの値を渡してコンストラクタで生成する。引数変換だけの `create()` は定義しない。Primitiveの正規化・単一値検証と、モデルの組み合わせの不変条件を分担する。[詳細](references/domain-layer.md)
- **暗黙の変換を避ける**: モデルの `__post_init__()` で基本型をPrimitiveや不変コレクションへ変換しない。単一値の検証・整形はPrimitiveが所有し、利用側はその生成結果を渡す。原文を保持する値は、その契約に応じて正規化と空値の扱いを定義する。
- **依存性逆転 (DIP)**: 上位層は抽象（Interface）に依存。Interfaceは上位層で定義。[詳細](references/dependency-inversion-principle.md)
- **データフロー**: `Presentation` $\rightarrow$ `Application` $\rightarrow$ `Domain` $\rightarrow$ `Repository Interface` (実行は `Infrastructure`)
- **Domainの標準配置**: 小規模なドメインは `domain/primitives.py`、`value_objects.py`、`entities.py`、`repositories.py`、`services.py`、`exceptions.py` の直下モジュールに分ける。責務別ディレクトリや互換用Facadeは増やさない。[詳細](references/domain-layer.md)
- **トランザクション (UoW)**: `Application` 層でコミット/ロールバック制御。`Infrastructure` 内でのコミット禁止。[詳細](references/unit-of-work.md)
