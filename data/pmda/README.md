# PMDA添付文書 データ作成・構造化ツール（backend CLI）

医薬品医療機器総合機構（PMDA）が公開する医療用医薬品添付文書（XML形式）をパースし、検索・対話AI向けの構造化JSONおよびSQLite全文検索（FTS5）インデックスを生成するツール群です。

## ディレクトリ構成

- `originals/`: 元XMLと図（移行時はbyte不変）
- `structured/`: 既存検索用document/JSONL/validation/manifest/SQLite
- `imports/`: Web取り込み不変版と登録世代の検索成果物。登録成功時にSQLiteのactive世代と候補へ即時反映します。
- `migration-artifacts/`: 元ignored一時成果物の保全先
- 変換正本: `backend.infrastructure.pmda_xml`、入口: `backend.infrastructure.cli.structure_pmda_xml`
- 辞書の純粋変換: `backend.application.medicine.autocomplete`、CSV境界: `backend.infrastructure.sources.yj_csv`

項目・列の共有定義は[package_inserts](../../package_inserts/README.md)を編集します。原文見出しと本文を共有定義で上書きしません。

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
- 全文検索用SQLiteインデックスはバックエンドが構造化データから作成

検索単位は文書キーと項目番号の組ごとに1レコードです。例えば `11.2` の
分類・頻度・副作用セル、表の行、内部の箇条書きは同じレコードの本文へ収めます。
`10.1` と `10.2` のような別項目は分け、親項目にはその項目自身の本文だけを残します。
子項目だけを持つ空の親項目は出力しません。`document.json` の原文構造は保持します。

上記のoffline変換は、JSONLを再生成しても公開検索へ登録しません。登録済み版の所有artifactへの直接上書きは拒否します。
新しいXMLを公開する場合はWeb取り込みか明示登録CLIを使用してください。移行・初期登録済みDBに対する登録CLIの例です。

```bash
uv run --project backend --locked python -m backend.infrastructure.cli.structure_pmda_xml \
  copy/new.xml --register --index-path copy/index.sqlite3 --import-dir copy/imports
```

`pnpm build:data`も登録modeです。`build_search_index`は既に登録されたactive集合を検証・再構築する入口であり、未登録XMLの自動走査や旧版の再登録は行いません。

```bash
uv run --project backend python -m backend.infrastructure.cli.build_search_index \
  --structured-dir data/pmda/structured \
  --index-path data/pmda/structured/.chat-search.sqlite3
```

索引の整合判定には、登録されたactive集合の実内容を使います。未準備・不整合では起動を拒否し、自動再構築はしません。

## Web取り込みと版の置換

`/imports`と`POST /api/attachment-imports`は原XML・生成物を保存した後、検索DBへ即時登録します。アップロードは運用中の検索対象と候補を変更する操作です。同YJは原XMLの改訂日によらず初回成功登録順で新版へ切り替えます。旧文書A+Bに新文書Aを登録した場合、Bは旧版を保持します。active参照とreader leaseがなくなった旧版の所有XML・JSON・JSONL・図だけを削除し、同原本の再送で旧版を復活させません。登録用YJがないXMLは拒否されます。

旧DBはbackend/writerを停止し、整合backupと別コピーでの復元検査を行った上で、Alembic移行と初期登録を明示実行してください。[backendの導入手順](../../backend/README.md#検索インデックスの構築)に従い、まずコピー先で検証します。初期登録後だけWeb/APIまたは`--register`で新版を公開し、旧原本群を初期登録CLIで再走査しません。

## 補完辞書

`uv run --project backend --locked python -m backend.infrastructure.cli.build_autocomplete_index --csv-path yj/y_ALL_sample.csv --output <明示出力>`。
既定入力探索は`yj/`と`data/pmda/yj/`、既定出力は`frontend/public/data/medicines.json`と`data/pmda/structured/medicines_autocomplete.json`です。CP932、有効期限、n/k/h/y/g/cの契約を維持します。

## 既存運用のパス変更

旧data_tools/data→data/pmda/originals、旧data_tools/structured→data/pmda/structured。
保存済みJSON内の旧source pathは歴史的出典として保持しています。元データを再生成せず移行しました。
明示MEDI_CHAT_STRUCTURED_DIR/MEDI_CHAT_INDEX_PATH/MEDI_CHAT_DATABASE_URLは優先を維持します。旧pathの運用設定は移行先へ明示変更してください。明示旧DBを別DBへ自動切替えません。
新しいWeb版はpublisherが即時公開します。手動でstructuredへ配置する操作や、Web登録後のbuild_search_index実行は不要です。
