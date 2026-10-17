---
name: application-layer
description: ドメイン駆動設計のアプリケーション層ルール
---

# Application Layer

ユースケースの実現と処理フローの制御を担う層。

## 1. 責務・制約
- **責務**: ユースケースの進行制御（オーケストレーション）、ドメインオブジェクト・ドメインサービスの呼び出し、外部ポート（Protocol）の定義、外層（Presentation / Infrastructure）に対する境界型・例外変換の提供。
- **制約（Import Linter強制）**:
  - `Domain` 層と標準ライブラリのみに依存し、`Presentation`・`Infrastructure`・`Config` には一切依存しない（`Application does not depend on outer layers`）。
  - 自身にドメイン固有のビジネスルールを持たず、ドメインオブジェクトへ委譲する。

## 2. 構成要素とコンテキスト間の有向パイプライン境界
1. **Application Service (`ChatApplicationService`, `AttachmentImportService` 等)**:
   - ユースケースに必要なポート（Reader/Repository/Classifier/Extractor/Policy/Provider）の束を保持し、複数ユースケース（`search_keywords`, `prepare_reply`, `stream_answer`, `answer_question` 等）をオーケストレーションする。
   - `Presentation` 層にユースケース束ねや業務オーケストレーションを漏らさない。
2. **ドメインサービスのカプセル化**:
   - `MedicineSuggester.from_registered_medicines(...)` のように、ドメインサービス（`get_weighted_aliases` 等）の呼び出しは Application 層のファクトリやユースケース内に閉じ込め、Composition Root や Infrastructure が `domain.*.services` を直接呼ばなくて済むようにする。
3. **コンテキスト間の有向パイプライン境界（Import Linter強制）**:
   - `chat -> retrieval -> medicine`
   - `attachment_import -> indexing -> medicine`
   - 下流コンテキスト（`medicine` や `retrieval`）から上流（`chat` 等）への逆依存は禁止する。
   - `*_models.py` は他の `*_models.py` と `domain` のみ、`*_contracts.py` は `*_models.py` / `*_contracts.py` と `domain` のみを参照でき、具象ユースケース実装への逆依存を禁止する。

## 3. 典型的な処理フロー
```text
1. 取得: 注入された Port / SnapshotProvider / Repository 経由でドメインモデルを取得
2. 実行: Domain Entity / Value Object / Domain Service を呼び出して業務判断・統合を実行
3. 変換・返却: フレームワーク非依存の Application モデルを返却（ドメイン例外は必要に応じて境界で変換）
```

## 4. Domain Service との比較
| 項目 | Application Service | Domain Service |
| :--- | :--- | :--- |
| **役割** | ユースケース（手順・シナリオ・ポート連携）の進行 | 複数ドメインオブジェクトにまたがる純粋なビジネスルール |
| **依存** | Repository Interface / 外部サービス Port (`Protocol`) | 外部非依存（ドメインオブジェクトのみ） |
