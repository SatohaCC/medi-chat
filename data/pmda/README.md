# PMDA添付文書 データ作成・構造化ツール（backend CLI）

医薬品医療機器総合機構（PMDA）が公開する医療用医薬品添付文書（XML形式）をパースし、確認用の構造化JSONを生成し、明示登録ではPostgreSQLへ原本bytes・完全構造・検索投影を保存するツール群です。

## ディレクトリ構成

- `originals/`: 元XMLと図（移行時はbyte不変）
- `structured/`: 既存の回帰テストが比較に使うdocument/JSONL。runtimeは読みません。不要な旧SQLite・索引・validation出力・重複辞書は削除済みです。
- `current-v4/`: 原本フォルダと重複しない取り込みXMLを1件だけ保持。旧SQLite・世代・構造化出力は削除済みで、runtimeは読みません。
- 過去の`imports/`（原本は`originals/`とbyte一致）と`migration-artifacts/`（pytestキャッシュ）は削除済みです。
- 変換正本: `backend.infrastructure.pmda_xml`、入口: `backend.infrastructure.cli.structure_pmda_xml`
- 辞書の純粋変換: `backend.application.medicine.autocomplete`、CSV境界: `backend.infrastructure.sources.yj_csv`

項目・列の共有定義は[型付き定義と技術設定のREADME](../../backend/infrastructure/package_insert_definitions/README.md)に従います。項目番号・正式名称・Scopeと相互作用列は[Domainの定義](../../backend/domain/attachment/value_objects.py)、XMLタグとの対応は[XML設定](../../backend/infrastructure/package_insert_definitions/xml_settings.py)を編集します。常時取得項目や質問に応じた検索方針は[Applicationの検索方針](../../backend/application/retrieval/standard_policies.py)で別に管理します。原文見出しと本文を共有定義で上書きしません。

## 実行方法

XML構造化CLIと補完辞書生成CLIの相対入力・出力パスは、
実行ディレクトリではなくリポジトリルートを基準に解決します。
絶対パスの明示指定も利用できます。補完辞書の自動検出は
リポジトリ内の`yj/`と`data/pmda/yj/`を検索します。

### 1. 全文書のoffline構造化（公開登録なし）

```bash
uv run --project backend --locked python -m backend.infrastructure.cli.structure_pmda_xml \
  --source-dir data/pmda/originals \
  --output-dir data/pmda/structured
```

### 2. 単一文書の構造化（テスト・確認用）

```bash
uv run --project backend --locked python -m backend.infrastructure.cli.structure_pmda_xml \
  data/pmda/originals/<薬品ディレクトリ>/<XMLファイル>.xml \
  --output-dir data/pmda/structured/<文書キー>
```

### 3. 生成される成果物

- 各文書の `document.json`: 原文XMLの階層、メタデータ、節索引
- 各文書の `search_units.jsonl`: 項目番号ごとに1行のJSON（本文・表・文脈見出し・出典）
- 各文書の `validation.json`: 原文の網羅性、参照先、図ファイルの検証結果
- 公開登録の検索投影はPostgreSQL内で保持し、offline JSONLを読み戻しません。

検索単位は文書版と大項目番号ごとです。子項目の本文・表・見出し・文脈を親の大項目レコードへ順序付きで保持し、10.1/10.2の検索でも大項目10を返します。完全Domain構造は子階層や参照・表cell・図を別途保持します。

`pnpm build:data`はoffline変換だけです。公開登録は明示migration・初期登録後のWebまたは次のCLIを使います。

```bash
uv run --project backend --locked python -m backend.infrastructure.cli.structure_pmda_xml new.xml --register --database-env MEDI_CHAT_DATABASE_URL
```

PGの完全構造から検索投影を再構築する場合は`pnpm db:rebuild`を明示します。原本再decode・旧JSONL再走査は行わず、原本/図・receipt・公開世代は保持します。未準備・不整合では起動を拒否し、起動時に自動migration/初期登録/清掃/再構築は行いません。

## Web取り込みと版の置換

`/imports`と`POST /api/attachment-imports`は原XMLbytea・完全構造・検索投影を一つのDB transactionで公開し、候補へ反映します。同YJは改訂年月の最新を採用し、同年月の別原本は409、年月なしは422です。旧A+Bに新Aを登録しても旧Bは保持します。参照0payloadのDB清掃は旧MVCC読取を妨げず、同原本再送で旧版を再有効化しません。登録用YJなしは拒否します。

旧SQLiteや保存JSONLの互換読み取り・移行はありません。原本・図・手作業データを保持し、空PGへの初期登録を明示してください。[backendの導入手順](../../docs/backend-design.md#検索インデックスの構築)を参照してください。初期登録は非空台帳を拒否します。

## 補完辞書

`uv run --project backend --locked python -m backend.infrastructure.cli.build_autocomplete_index --csv-path yj/y_ALL_sample.csv --output <明示出力>`。
既定入力探索は`yj/`と`data/pmda/yj/`、既定出力は`frontend/public/data/medicines.json`と`data/pmda/structured/medicines_autocomplete.json`です。CP932、有効期限、n/k/h/y/g/cの契約を維持します。

## 既存運用のパス変更

旧data_tools/data→data/pmda/originals、旧data_tools/structured→data/pmda/structured。
保存済みJSON内の旧source pathは歴史的出典として保持しています。元データを再生成せず移行しました。
runtimeの接続先は`MEDI_CHAT_DATABASE_URL`です。旧`MEDI_CHAT_STRUCTURED_DIR`/`MEDI_CHAT_INDEX_PATH`/`MEDI_CHAT_IMPORT_DIR`は拒否します。入力XMLやoffline出力の相対パスはroot基準ですが、runtimeはそれらへ依存しません。

## ローカルデータについて

実添付文書のXML・図、本文を含む構造化JSON/JSONL、登録世代データ、実データ由来のoracle・SQLite fixtureはGit管理対象外です。各自のローカル環境に用意し、リポジトリへ追加しないでください。項目体系の定義・変換コードと、合成データのテストは引き続き管理します。

実データを使う回帰テストにはローカルの原本・比較用JSON/JSONLが必要です。データがないcheckoutで、その検証が成功したとは扱いません。不要なローカル生成物を整理しましたが、原本・比較用データ・コード・テストの期待値は変更していません。
