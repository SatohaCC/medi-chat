# medi-chat (医療・医薬品AI対話システム)

Next.js と FastAPI をベースにした、PMDA（医薬品医療機器総合機構）添付文書の検索・根拠引用（RAG）およびリアルタイムストリーミング対話AIチャットシステムです。

**pnpm 12.4+ のマルチ言語ワークスペース機能（JavaScript + Python）により、リポジトリ全体を一元管理しています。**

---

## ローカルPostgreSQLの準備

通常backendはPostgreSQLだけを使用します。原XML・図のbytes、完全な文書構造、検索投影、登録結果をDBで保持し、起動時に入力ディレクトリを読みません。

1. Docker Desktopを起動し、rootの`.env.postgres.example`を`.env.postgres`へコピーして管理・migration owner・runtimeの別々のパスワードを設定します。`docker compose --env-file .env.postgres up -d --wait`でPostgreSQL 18をloopback `127.0.0.1:15432`に起動します。
2. fresh named volumeの初回だけ`scripts/postgres/init.sh`が`medi_chat_dev`/`medi_chat_test`と`medi_chat_owner`/`medi_chat_app`を作ります。両roleは非superuser・DB/role作成不可、ownerだけがschema DDLを担当し、runtimeはDMLを使います。既存volumeでは初期化scriptは再実行されません。既存DBを初期化するためのvolume削除は行わないでください。
3. `backend/.env.example`のPG URL例に従い、owner/runtime/testの接続先をローカル環境変数へ設定します。パスワードはURL encodeします。管理者接続はアプリへ渡しません。CLIの`--database-env`はURLを保持する環境変数名を明示します。
4. owner URLを`MEDI_CHAT_MIGRATION_DATABASE_URL`へ設定し、rootから`pnpm db:migrate`を明示実行します。接続URLをコマンド引数へ貼り付ける必要はありません。通常起動・publisherはDDLを実行しません。
5. `pnpm db:initialize`で空DBへXML/図を登録します。図の参照先欠損/危険path/symlinkを含む初期登録は拒否し、非空DBは置換しません。既存原本・SQLite・生成物は保持します。
6. 保持原本の明示exportは同CLIの`export --version-id <document_id:sha256> --output-dir <新規出力先>`、清掃は`maintenance`です。exportは`source.xml`と`figures/`へ元bytesを出し、stdoutに元filename/hash/byte数を返します。清掃後はtombstoneだけを保持し、旧版再送でpayloadを復活させません。

実PG試験は専用`medi_chat_test`、owner/app URLを`TEST_DATABASE_URL`/`TEST_RUNTIME_DATABASE_URL`へ設定して実行します。各試験は`medi_chat_test_<run>`schemaだけを作成・削除します。test名のURLだけでdev DBを使うことはできません。接続情報をログや共有文書へ貼り付けないでください。

CIの`Synthetic PostgreSQL contracts`は、job所有のPG18 service・非superuser owner/runtime・UUIDschemaで合成XMLの実DB契約と静的ゲートを実行します。原本集合はGit管理外のため配布・自動取得せず、原本を使う全試験・実ブラウザ・性能はデータを準備したPCで実行します。CI部分試験だけを全移行検証とは扱いません。

## 🎯 プロジェクトの目的

本プロジェクトは、調剤薬局や医療現場において日々膨大な医薬品情報を確認・判断する**薬剤師の意思決定を迅速かつ確実にサポートすること**を目的としています。

1. **薬剤師の意思決定をサポート**
   - 疑義照会、併用禁忌・相互作用チェック、患者背景に応じた用量調節、服薬指導などの臨床・調剤実務において、根拠となる電子添文の正確な記載を即座に引き出し、判断のスピードと安全性を向上させます。

2. **添付文書を低コストで参照させる仕組みの検討・実現**
   - 高額な商用ベクトルデータベースや過剰な外部LLMトークン消費に依存せず、PMDA公式のXML電子添文を構造化し、PostgreSQLと決定論的な項目・日本語trigram phrase検索を使って該当条項を取得します。順位は独立SQLite FTS5 oracleと照合しています。
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
│   ├── main.py           # FastAPI アプリ生成・ルーター登録（Lifespan配線は infrastructure/composition へ委譲）
│   ├── alembic.ini       # Alembic マイグレーション設定
│   ├── presentation/     # 公開DTO・mapper・AppChatService・REST/WS・dependencies.py（Depends集約）
│   ├── application/      # ChatApplicationService・ユースケース・チャットストリーム制御
│   ├── config/           # 接続設定・生成default供給
│   ├── domain/           # 一つの医薬品情報意思決定支援ドメイン（医薬品同定・根拠検索・添付文書）
│   ├── infrastructure/   # SQLAlchemy Core・Janome・TypeSafe・LLM・XML・CLI・composition(app_lifespan)
│   ├── migrations/       # Alembic リビジョン定義
│   ├── tests/            # API・WebSocket・永続化・マイグレーション・アーキテクチャ境界の自動テスト
│   ├── pyproject.toml    # Python 依存設定・Ruff・Import Linter（全24契約）
│   ├── pylock.toml       # uv.lock から uv export で生成する Python ロックファイル
│   ├── package.json      # pnpm 連携スクリプト（dev, test, lint, format）
│   └── .env.local        # APIキー環境変数（GEMINI_API_KEY, OPENAI_API_KEY）
│
├── data/pmda/           # 原本・構造化成果物・保管版
│   ├── originals/       # 原本XML・図
│   ├── structured/      # offline確認用JSON・過去の生成物（runtime未使用）
│   └── imports/         # Web取り込み版と登録世代の検索成果物
│
├── docs/                 # 仕様書・設計ドキュメント
└── README.md
```

バックエンドの責務分担、依存関係、モジュールの移動先は [backend/README.md](backend/README.md) を参照してください。

添付文書の項目・質問意図・キーワード・Jev分類・プロンプト用の定義・XML対応は、[Infrastructure定義ソース](backend/infrastructure/package_insert_definitions/package_insert_catalog.json) で一元管理します。[編集方法](backend/infrastructure/package_insert_definitions/README.md) に参照規則と検証方法を記載しています。用途別のモデルをbackend内のattachment/retrieval/Applicationへ投影し、技術設定はInfrastructureが所有します。Python実行にはbackendの配置を使用します。

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

## 🔍 リンター & フォーマッター（アーキテクチャ制約の自動強制）

フロントエンドは **Biome**、Python コードは **Ruff** と **Import Linter（全24契約）** を採用しています。
特にバックエンドでは、オニオンアーキテクチャのレイヤー間境界（`Presentation -> Domain` の完全禁止など）だけでなく、レイヤー内部のモジュール階層・アダプター間の相互独立までリンターで機械的に強制することで、実装時の判断コストを削減し開発効率を高めています。

ルートからワンコマンドで全領域のチェック・フォーマットを実行できます：

```bash
# 全ワークスペースのリント・フォーマット一括チェック＆自動修正
pnpm check

# リントのみチェック（Biome + Ruff + Import Linter 24契約）
pnpm lint

# コード整形（フォーマット）のみ適用
pnpm format

# 型検査の一括実行 (TypeScript: tsc + Python: Pyright)
pnpm typecheck
```

個別実行の場合：
```bash
pnpm --filter frontend check        # Biome
pnpm --filter backend check         # Ruff チェック・フォーマット & Import Linter
pnpm --filter backend lint          # Ruff + Import Linter（24契約）
pnpm --filter backend lint:imports  # Import Linter（依存境界契約のみ高速実行）
pnpm typecheck:frontend             # TypeScript (tsc)
pnpm typecheck:python               # Python (Pyright / Pylance同等エンジン)
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

原XMLを確認用JSONへoffline変換する場合（公開検索は更新しません）：

```bash
pnpm build:data
```

## ブラウザからのXML取り込み・検索登録

`/imports`でPMDAのXMLを1つ選択して送信します。原本bytea・完全構造・検索投影をDBへ保存し、登録成功時にactive世代と医薬品候補へ即時反映します。保管だけを行う操作ではありません。文書情報・改訂・件数・図欠落などの警告に加えて、登録・置換・削除待ちの状態を表示します。

同じYJコードは原XMLの改訂年月（YYYY-MM）が最も新しい添付文書を採用します。古い文書を後から登録しても公開先を戻しません。同じ改訂年月の別原本は409、改訂年月の欠落は422で拒否します。旧文書の別YJがまだactiveなら旧版を保持し、active参照がなくなった版の保持payloadをDBで回収します。進行中の読取はread-only REPEATABLE READ/MVCCで旧版を一貫して参照できます。同一原本の再送は以前の版を再有効化しません。

保存先は`MEDI_CHAT_DATABASE_URL`で明示したPostgreSQLです。旧SQLite/JSONLの移行・互換読取は提供せず、空DBへ原本から初期登録します。起動時の自動DDL・初期登録・清掃はありません。整合した清掃待ちは起動を妨げず、`pnpm db:maintenance`または登録後の限定再試行で収束させます。原本exportや完全構造からの検索投影rebuildは[backendの手順](backend/README.md#検索インデックスの構築)を参照してください。XMLは10MiB、multipart全体は11MiB、変換成果物は32MiBまでです。

`POST /api/attachment-imports`はmultipartの`file`1つを受け取り、新規201・同一原本の再送200とLocationを返します。LocationへのGETで保存結果を再読込できます。原本や保存先を取得する公開APIはありません。

XML取り込み画面には登録履歴を新しい登録順で表示します。`GET /api/attachment-imports?limit=20&offset=0`はファイル名・製品・改訂年月・現在適用中のYJ・保存データ削除状態を返します（limitは1～100、既定50）。削除済み旧版も履歴に残り、ファイル名が失われている場合は文書IDを表示します。一覧は初回・手動更新・取り込み成功時に取得し、定期ポーリングは行いません。

通常の`pnpm test:e2e`は、通常devと同じdotenv設定で選択したPostgreSQLのread-only readinessと実backendのhealthを確認した後、モック画面と実接続の両suiteを実行します。未準備・不整合のDBでは非0で停止し、自動再構築はしません。backend起動確認は専用ポート3212でhealthだけを要求し、試験所有processだけを終了します。

個別実行は`pnpm --filter frontend test:e2e:mock`と`pnpm --filter frontend test:e2e:real`です。実接続は専用ポート3110/3211と専用`medi_chat_test`内の試験所有UUIDschemaを使い、APIをinterceptせず、外部LLM keysを空・dotenv無効にします。原本から登録したPG fixtureで版の置換・旧一部保持・削除・旧再送非復活・再起動を確認し、configured dev DBには書き込みません。Nextの試験出力は`.next-e2e-mock`/`.next-e2e-real`へ分離し、通常devの`.next`を共有しません。
