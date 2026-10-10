# PMDA添付文書 データ作成・構造化ツール（data_tools）

医薬品医療機器総合機構（PMDA）が公開する医療用医薬品添付文書（XML形式）をパースし、検索・対話AI向けの構造化JSONおよびSQLite全文検索（FTS5）インデックスを生成するツール群です。

## ディレクトリ構成

- `data/`: PMDAから入手した原本XMLデータ（製品ごとのZIP解凍フォルダ）
- `structured/`: 構造化処理後のJSONおよびSQLiteデータベース（`.chat-search.sqlite3`）
- `structure_pmda_xml.py`: CLIと既存の `transform()` 呼び出し口
- `pmda_xml/xml_nodes.py`: XML原文の保持、テキスト化、文書メタデータ
- `pmda_xml/sections.py`: 共通カタログに従ってXML内の節を検索
- `pmda_xml/units.py`: XMLから検索単位を生成
- `pmda_xml/transform.py`: 検証とJSON成果物の書き出し
- `../package_inserts/package_insert_catalog.json`: backendと共有する項目番号・名称・XMLタグ・表の列定義

項目や列の定義は [共通カタログ](../package_inserts/README.md) を編集します。`data_tools` と `backend` は標準ライブラリだけで動く `package_inserts` に依存し、互いには依存しません。XML本文や文書固有の見出しは原文を保持します。タグの別名と祖先に依存する `OtherInformation` の解釈もカタログが管理します。

## 実行方法

### 1. 全文書の構造化とインデックス作成

```bash
uv run --project data_tools python -m data_tools.structure_pmda_xml \
  --source-dir data_tools/data \
  --output-dir data_tools/structured
```

### 2. 単一文書の構造化（テスト・確認用）

```bash
uv run --project data_tools python -m data_tools.structure_pmda_xml \
  data_tools/data/<薬品ディレクトリ>/<XMLファイル>.xml \
  --output-dir data_tools/structured/<文書キー>
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

XML変換後は、アプリが参照するSQLite索引も明示的に再構築してください。
JSONLの再生成だけでは検索結果は更新されません。

```bash
uv run --project backend python -m backend.infrastructure.cli.build_search_index \
  --structured-dir data_tools/structured \
  --index-path data_tools/structured/.chat-search.sqlite3
```

索引の更新判定にはmanifestだけでなく、各`document.json`と`search_units.jsonl`の
内容を使います。古い索引が残っている場合、起動時に再構築を要求します。
