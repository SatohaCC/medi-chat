---
name: unit-of-work
description: Unit of Work (UoW) パターンのルール
---

# Unit of Work (UoW)

単一のユースケースにおける複数のデータ変更操作の原子性（All or Nothing）を保証するパターン。

## 1. 責務・制約
- **責務**: トランザクション境界の統一管理、アトミックな更新（コミット/ロールバック）の保証。
- **制約**:
  - トランザクションの境界・確定（Commit）・破棄（Rollback）の制御は **Application Layer** で行う。
  - Repository（Infrastructure Layer）内部で Commit を呼び出すことは禁止。
  - Domain Layer は UoW の存在に非依存。

## 2. 構成要素
1. **IUnitOfWork (Interface)**: トランザクション開始・Commit・Rollback の抽象定義。
2. **Concrete UoW**: 特定のデータベース技術に依存した UoW の具象実装。
3. **Repository Accessor**: 同一トランザクション内で動作するリポジトリ群へのアクセス機構。
