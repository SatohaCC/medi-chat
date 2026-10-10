---
name: infrastructure-layer
description: ドメイン駆動設計のインフラストラクチャ層ルール
---

# Infrastructure Layer

データベース・外部API・ネットワーク等の技術的詳細を実装する層。

## 1. 責務・制約
- **責務**: データの永続化・復元、外部システム連携、技術的詳細の隠蔽。
- **制約**: 上位層で定義された Interface に依存し具体的な実装を提供する（DIP）。ビジネスロジックを含めない。

## 2. 構成要素
1. **Repository Implementation**: Domain層の `Repository Interface` を具体的なDB技術で実装。
2. **Data / ORM Models**: データベースの構造に合わせたデータモデル（Domain Entity とは区別）。
3. **External Adapters**: 外部API通信・キャッシュ・メッセージング等の実装。

## 3. Repositoryの役割 (マッピング)
- **保存**: Domain Entity $\rightarrow$ DB Model への変換 $\rightarrow$ DB書き込み
- **取得**: DB読み込み $\rightarrow$ DB Model $\rightarrow$ Domain Entity への復元

## 4. 依存性注入 (DI)
上位層（Application層等）は具象クラスを直接参照せず、構成の根幹（Composition Root）で具象実装を注入する。
