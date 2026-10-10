# medi-chat (医療・医薬品AI対話システム)

Next.js と FastAPI をベースにした、PMDA（医薬品医療機器総合機構）添付文書の検索・根拠引用（RAG）およびリアルタイムストリーミング対話AIチャットシステムです。

**pnpm 12.4+ のマルチ言語ワークスペース機能（JavaScript + Python）により、リポジトリ全体を一元管理しています。**

---

## 🎯 プロジェクトの目的

本プロジェクトは、調剤薬局や医療現場において日々膨大な医薬品情報を確認・判断する**薬剤師の意思決定を迅速かつ確実にサポートすること**を目的としています。

1. **薬剤師の意思決定をサポート**
   - 疑義照会、併用禁忌・相互作用チェック、患者背景に応じた用量調節、服薬指導などの臨床・調剤実務において、根拠となる電子添文の正確な記載を即座に引き出し、判断のスピードと安全性を向上させます。

2. **添付文書を低コストで参照させる仕組みの検討・実現**
   - 高額な商用ベクトルデータベースや過剰な外部LLMトークン消費に依存せず、PMDA公式のXML電子添文をローカルで精緻に構造化（SQLite FTS5 + 決定論的ルール検索）。**極めて低コストかつ高速（1~2ms）に該当条項を特定できるアーキテクチャ**を探求・検証しています。
   - ルール検索をベースとしつつ、質問文の曖昧なニュアンスや複合意図の補完に軽量AI（Jev等）をハイブリッド統合することで、高精度と低運用コストを両立します。

3. **薬剤師向けに特化したUI/UXの構築**
   - 医療従事者の思考・確認プロセスに即したインターフェースを追求。
   - YJコード／医薬品名のインクリメンタルサジェスト、添付文書項目ごとの構造化カード表示、改訂年月・版数の明示、PMDA原本へのワンクリック出典リンク、検索由来（ロジック取得 / AI判定補完）のバッジ表示など、現場で直感的に信頼できる操作感を提供します。

---

## 📁 プロジェクト構成

リポジトリ直下の `pnpm-workspace.yaml` により、フロントエンド（Next.js）およびバックエンド・データツール（Python）の全パッケージを `pnpm` で一元管理しています：

```text
medi-chat/
├── pnpm-workspace.yaml   # pnpm 12 マルチ言語ワークスペース設定（python: enabled: true）
├── package.json          # ルート統合スクリプト（dev, test, check, build 等）
├── pnpm-lock.yaml        # ルート統合ロックファイル
│
├── frontend/             # 1. フロントエンド（Next.js App Router）
│   ├── app/              # 画面コンポーネント・チャットUI
│   ├── biome.json        # Biome リンター・フォーマッター設定
│   └── package.json      # Next.js 依存設定
│
├── backend/              # 2. バックエンド（FastAPI + WebSocket + SQLAlchemy Core + Alembic）
│   ├── main.py           # FastAPI アプリ生成・Lifespan・依存の組み立て
│   ├── alembic.ini       # Alembic マイグレーション設定
│   ├── presentation/     # 公開DTO・mapper・REST/WS・依存関係（Depends）
│   ├── application/      # ユースケース・チャットストリーム制御
│   ├── config/           # 接続設定・生成default供給
│   ├── domain/           # 一つの医薬品情報意思決定支援ドメイン（医薬品同定・根拠検索）
│   ├── infrastructure/   # SQLAlchemy Core・Janome・TypeSafe・LLM・CLI・composition
│   ├── migrations/       # Alembic リビジョン定義
│   ├── tests/            # API・WebSocket・永続化・マイグレーションの自動テスト
│   ├── pyproject.toml    # Python 依存設定（FastAPI, SQLAlchemy, Alembic, OpenAI 等）
│   ├── pylock.toml       # uv.lock から uv export で生成する Python ロックファイル
│   ├── package.json      # pnpm 連携スクリプト（dev, test, lint, format）
│   └── .env.local        # APIキー環境変数（GEMINI_API_KEY, OPENAI_API_KEY）
│
├── data_tools/           # 3. 事前データ作成・構造化ツール系
│   ├── structure_pmda_xml.py  # PMDA電子添文XMLパーサー・JSON構造化CLI
│   ├── data/             # 原本XMLデータ（薬品ごとの解凍データ）
│   ├── structured/       # 構造化出力（JSON & SQLite全文検索インデックス）
│   ├── tests/            # パイプライン単体テスト
│   ├── pyproject.toml    # データ作成ツールの Python 依存設定
│   ├── pylock.toml       # pnpm が生成する Python ロックファイル
│   ├── package.json      # pnpm 連携スクリプト（test, lint, build-data）
│   └── README.md
│
├── package_inserts/      # backend/data_tools共通の添付文書カタログと検証・整形
├── docs/                 # 仕様書・設計ドキュメント
└── README.md
```

バックエンドの責務分担、依存関係、モジュールの移動先は [backend/README.md](backend/README.md) を参照してください。

添付文書の項目・質問意図・キーワード・Jev分類・プロンプト用の定義・XML対応は、[共通カタログ](package_inserts/package_insert_catalog.json) で一元管理します。[編集方法](package_inserts/README.md) に参照規則と検証方法を記載しています。Pythonの実行環境には `backend` / `data_tools` とともに `package_inserts` を配置してください。

---

## 🛠️ 開発・起動手順

### 1. 全依存関係の一括インストール

ルート直下で `pnpm install` を実行するだけで、**Next.js の npm パッケージ** と **FastAPI / データツールの Python パッケージ（PyPI）** が並行して一括インストールされます：

```bash
# 全ワークスペース（JS + Python）の依存関係を一括取得
pnpm install
```

### 2. 環境変数の設定

`backend/.env.local` に API キーを設定します：

```env
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. サーバー起動

ルートから一括起動、または個別起動が可能です：

**フロントエンド & バックエンドを同時に起動**:
```bash
pnpm dev
```

**個別起動**:
```bash
# バックエンド (FastAPI: http://localhost:8000)
pnpm run dev:backend

# フロントエンド (Next.js: http://localhost:3000)
pnpm dev:frontend
```

---

## 🔍 リンター & フォーマッター

フロントエンドは **Biome**、Python コードは **Ruff** を採用しています。ルートからワンコマンドで全領域のチェック・フォーマットを実行できます：

```bash
# 全ワークスペースのリント・フォーマット一括チェック＆自動修正
pnpm check

# リントのみチェック
pnpm lint

# コード整形（フォーマット）のみ適用
pnpm format

# 型検査の一括実行 (TypeScript: tsc + Python: Pyright)
pnpm typecheck
```

個別実行の場合：
```bash
pnpm --filter frontend check      # Biome
pnpm --filter backend check       # Ruff
pnpm --filter data_tools check    # Ruff
pnpm typecheck:frontend           # TypeScript (tsc)
pnpm typecheck:python             # Python (Pyright / Pylance同等エンジン)
```

---

## 🧪 テスト実行

バックエンドとデータ作成ツールの単体・統合テストをルートから一括実行できます：

```bash
# 全テストの一括実行
pnpm test

# 個別実行
pnpm test:backend  # バックエンド（API, WebSocket）
pnpm test:data     # データ作成ツール（PMDA XMLパーサー）
```

---

## 📊 事前データ作成（data_tools）

PMDAの新規添付文書XMLをパースして検索インデックスを生成・更新する場合：

```bash
pnpm --filter data_tools run build-data
```
