---
name: presentation-layer
description: ドメイン駆動設計のプレゼンテーション層ルール
---

# Presentation Layer

外部（ユーザー・他システム）からの要求の受領と応答を担う最外層（API, Web UI, CLI, WS等）。

## 1. 責務・制約
- **責務**: 入力フォーマットの検証・解釈、Application Service の呼び出し、エラーハンドリング（HTTPステータス等の返却）。
- **制約**: ビジネスロジックを保持しない。データベースや Repository の直接参照・操作を禁止（必ず Application Service を経由）。

## 2. 構成要素
1. **Controllers / Routers**: エンドポイント定義と処理の委譲。
2. **Request / Response Schemas**: 入出力データの形式チェック・変換。
3. **DI Components**: 依存関係の組み立てと Application Service への注入。

## 3. リクエスト処理パターン
```text
1. 入力受領: リクエスト形式のバリデーション
2. 処理委譲: 検証済みデータを渡し Application Service を呼び出す
3. 応答返却: 実行結果をレスポンス形式へ変換して返却（例外は適切なエラーレスポンスへ変換）
```
