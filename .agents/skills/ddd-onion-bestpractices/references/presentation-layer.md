---
name: presentation-layer
description: ドメイン駆動設計のプレゼンテーション層ルール
---

# Presentation Layer

外部（ユーザー・他システム）からの要求の受領と応答を担う最外層（API, Web UI, CLI, WS等）。

## 1. 責務・制約
- **責務**: 入力フォーマットの検証・解釈、公開DTOとApplicationモデルの相互変換、Application Service の呼び出し、エラーハンドリング（HTTPステータス等の返却）。
- **厳格な依存制約（Import Linter強制）**:
  - **参照先は `Application`（および `Config`）のみ**。
  - **`Domain` 層および `Infrastructure` 層への直接 import は例外なく全面禁止**（`Presentation does not depend on domain` / `Presentation does not depend on infrastructure`）。
  - ドメイン例外（`DomainValidationError` 等）は Application Service の境界で標準例外や結果モデルに変換させ、Presentation が `backend.domain` を import しない構造を保つ。
  - 公開DTOの組み立てでは `dataclasses.asdict()` を使わず（Ruff `TID251` で禁止）、明示的な mapper と `.value` 変換を用いる。

## 2. レイヤー内部の単方向階層（Import Linter強制）
Presentation内部のモジュールは以下の単方向階層（上流 $\rightarrow$ 下流）に従う：
1. **Routes** (`chat_routes.py`, `medicine_routes.py`, `attachment_import_routes.py`, `system_routes.py`)
2. **DI Providers** (`dependencies.py`) — FastAPIの `Depends` 関数はすべてここに集約する。ルーター内に `request.app.state` を直接読む関数を定義しない。
3. **DTO Adapter Services** (`chat_service.py` の `AppChatService` 等) — 公開DTOとApplicationモデルを変換し、`ChatApplicationService` へ委譲する。
4. **DTO Mappers** (`chat_dto_mapper.py`) — Pydantic DTO と Application 入出力モデルの相互変換。
5. **Public DTO Models** (`chat_models.py`, `evidence_models.py`) — Pydantic スキーマ定義。

## 3. リクエスト処理パターン
```text
1. 入力受領: Router と Pydantic DTO でリクエスト形式をバリデーション + Depends(get_...) でサービス注入
2. DTO変換・委譲: Adapter / Mapper で Application モデルへ変換し Application Service を呼び出す
3. 応答返却: 実行結果を公開 DTO へ変換して返却（例外は適切な HTTP エラーレスポンスへ変換）
```
