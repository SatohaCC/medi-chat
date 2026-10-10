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

## 2. 構成要素
1. **Abstraction (Interface)**: 上位層で定義する「何をするか」のみを宣言した型定義。
2. **Low-level Module (Implementation)**: インフラ層で Interface を具象化した実装。
3. **Dependency Injection (DI)**: 外部から具象実装を注入し、直接的なインスタンス化を避ける仕組み。

## 3. 依存構造の対比
- **DIP非適用**: `Application` $\rightarrow$ `DB Implementation` （具象に依存・変更に脆い）
- **DIP適用**: `Application` $\rightarrow$ `Interface` $\leftarrow$ `DB Implementation` （抽象に依存・交換が容易）
