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
├── data/pmda/           # 原本・構造化成果物・保管版
│   ├── originals/       # 原本XML・図
│   ├── structured/      # 検索用JSON・既存SQLite
│   └── imports/         # Web取り込み版（検索への自動反映なし）
│
├── package_inserts/      # backend共通の添付文書カタログと検証・整形
├── docs/                 # 仕様書・設計ドキュメント
└── README.md
```

バックエンドの責務分担、依存関係、モジュールの移動先は [backend/README.md](backend/README.md) を参照してください。

添付文書の項目・質問意図・キーワード・Jev分類・プロンプト用の定義・XML対応は、[共通カタログ](package_inserts/package_insert_catalog.json) で一元管理します。[編集方法](package_inserts/README.md) に参照規則と検証方法を記載しています。Pythonの実行環境には `backend` とともに `package_inserts` を配置してください。

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
pnpm --filter backend check      # XML/辞書CLIも含むRuff
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

## 📊 事前データ作成（backend CLI）

単一/バッチXML変換、図の厳格検証、補完辞書生成とパス移行は[data/pmdaの作業案内](data/pmda/README.md)を参照してください。Python環境はbackendのuv.lockとPython 3.14へ統一し、pnpmのPython環境管理は無効化しています。

PMDAの新規添付文書XMLをパースして検索インデックスを生成・更新する場合：

```bash
pnpm build:data
```

## ブラウザからのXML保管

`/imports`でPMDAのXMLを1つ選択して送信します。元バイトと生成物を保管し、文書情報・改訂・件数・図欠落などの警告を表示します。検索SQLiteや既存structuredには自動反映しません。

保存先は既定で`data/pmda/imports`、`MEDI_CHAT_IMPORT_DIR`で変更できます。backendは従来どおり準備済み検索索引が必要です。XMLは10MiB、multipart受信全体は11MiB、生成4成果物はUTF-8合計32MiBまでです。

`POST /api/attachment-imports`はmultipartの`file`1つを受け取り、新規201・同一原本の再送200とLocationを返します。LocationへのGETで保存結果を再読込できます。原本や保存先を取得する公開APIはありません。

通常の`pnpm test:e2e`は、通常devと同じdotenv設定で解決した検索索引のread-only readinessと実backendのhealthを確認した後、モック画面と実接続の両suiteを実行します。未準備・staleの索引では非0で停止し、自動再構築はしません。backend起動確認は専用ポート3212でhealthだけを要求し、試験所有processだけを終了します。

個別実行は`pnpm --filter frontend test:e2e:mock`と`pnpm --filter frontend test:e2e:real`です。実接続は専用ポート3110/3211と一時prepared SQLite/import rootを使い、APIをinterceptせず、外部LLM keysを空・dotenv無効にします。実旧manifest索引の整合copyから実CLIで回復するケースも含み、元DBは更新しません。Nextの試験出力は`.next-e2e-mock`/`.next-e2e-real`へ分離し、通常devの`.next`を共有しません。
