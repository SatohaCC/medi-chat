---
name: infrastructure-layer
description: ドメイン駆動設計のインフラストラクチャ層ルール
---

# Infrastructure Layer

データベース・外部API・ネットワーク等の技術的詳細を実装する層。

## 1. 責務・制約
- **責務**: データの永続化・復元、外部システム（LLM, TypeSafe Jev, Janome, PMDA XML）連携、技術的詳細の隠蔽、および Composition Root での依存組み立て。
- **制約（Import Linter強制）**:
  - 上位層（`Domain` / `Application`）で定義された Interface (`Protocol`) に依存し具体的な実装を提供する（DIP）。
  - ビジネスロジックを含めず、また `domain.*.services`（ドメインサービス）を直接呼び出さない（Application層のユースケース・ファクトリ経由で扱う）。

## 2. インフラ内部の独立性・境界ルール（Import Linter強制）
1. **外部技術アダプター間の相互独立 (`External technology adapters are independent`)**:
   - `llm`、`intent`、`morphology`、`pmda_xml` の各アダプターパッケージは互いに一切 import しない。
2. **定義ローダーの独立 (`Package insert definitions do not depend on other infrastructure adapters`)**:
   - 単一JSON定義ローダー（`package_insert_definitions`）は他のアダプターに依存しない。各アダプター向けの設定型（`JevClassificationSettings`, `JanomeMorphologySettings`, `PmdaXmlSettings` 等）は `package_insert_definitions/definition_settings.py` が所有し、各アダプター側から単方向で参照する。
3. **永続化層と入力ソース・XMLアダプターの分離**:
   - `persistence` は `sources` に依存しない（`Persistence does not depend on input sources`）。
   - XMLに依存しないJSON/検索単位payloadのシリアライズ（`infrastructure/index_payloads.py`、`evidence_mapping.py`）は `infrastructure/` 直下に置き、アダプターパッケージには依存しない（`Infrastructure payload mappers do not depend on adapter packages`）。
   - `GenerationRuntime` や `SqliteRegistrationPublisher` が XML デコード／エンコードを必要とする場合は、`PmdaXmlDecoder` / `PmdaArtifactEncoder` をコンストラクタDIで注入する。
4. **Composition Root / CLI への逆依存禁止**:
   - 各アダプターは `composition` や `cli` に依存しない（`Infrastructure adapters do not depend on composition or CLI`）。

## 3. 依存性注入 (Composition Root)
- アプリケーション起動時の具象インスタンス生成・配線・Lifespan終了処理は `infrastructure/composition/app_lifespan.py`（`create_app_lifespan`）に集約し、`main.py`（`create_app`）はルーター登録と Lifespan 委譲のみを行う薄いエントリポイントに保つ。
