---
name: dependency-inversion-principle
description: 依存性逆転の原則 (DIP) のルール
---

# Dependency Inversion Principle (DIP)

上位モジュール（Domain/App）を下位の詳細（DB, API, FW）から分離・保護する設計原則。

## 1. 責務・制約
- **原則**: 「上位モジュールも下位モジュールも共に抽象（Interface）に依存する」。
- **所有権**: Interface の定義権限は呼び出し側（上位層: Domain または Application）が持つ。
- **依存の方向**: ソースコードの依存方向は外側から内側（抽象）に向かう。

## 2. 構成要素と2段階DI（FastAPI）
1. **Abstraction (Interface / `Protocol`)**: 上位層（`Domain` の `repositories.py` または `Application` の `*_contracts.py`）で定義する抽象型。
2. **Low-level Module (Implementation)**: `Infrastructure` 層で Protocol を具象化した実装。
3. **2段階の Dependency Injection (DI)**:
   - **第1段階（アプリ起動時 / Composition Root）**: `infrastructure/composition/app_lifespan.py`（`create_app_lifespan`）にて、DB Engine・Repository・外部SDKアダプター・Application Service・Adapter Service を生成・配線し、`app.state` に保持して終了時に確実に close/dispose する。
   - **第2段階（リクエスト時 / FastAPI `Depends`）**: `presentation/dependencies.py` に集約した `Depends` 関数で `app.state` からサービスを取り出し、各ルーターのエンドポイント引数へ注入する（テスト時は `app.dependency_overrides` で差し替え可能）。

## 3. 依存構造の対比
- **DIP非適用**: `Presentation / Application` $\rightarrow$ `Infrastructure Implementation` （具象に依存・変更に脆い）
- **DIP適用（Import Linterで機械強制）**: `Presentation` $\rightarrow$ `Application (Service / Port Protocol)` $\leftarrow$ `Infrastructure Implementation` （抽象に依存・交換が容易）
