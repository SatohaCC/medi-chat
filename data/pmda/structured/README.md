# PMDA電子添文の構造化データ

`data_tools.structure_pmda_xml` は、取得済みの医療用医薬品XMLを読み、原本を変更せずに次のファイルを生成します。

```powershell
uv run --project data_tools python -m data_tools.structure_pmda_xml 'data_tools/data/イグザレルト錠２．５ｍｇ/630004_3339003F5020_1_08.xml' --output-dir 'data_tools/structured/630004_3339003F5020_1_08'
```

| ファイル | 用途 |
| --- | --- |
| `document.json` | 製品・改訂情報、項目番号の索引、XMLの階層を保った本文。原文の属性、表の結合情報、脚注参照、改行指示、画像参照を残す。 |
| `search_units.jsonl` | チャット検索用の派生データ。本文を持つ項目番号ごとに1行のJSONを出力する。 |
| `validation.json` | 本文テキストの収録範囲、参照先、画像ファイルの検査結果。 |

`document.json` の `section_index` はPMDA XMLのタグと項目番号を対応させたものです。
欠番を埋めず、`sections[].tree` に原文の階層・属性・図・改訂情報を保持します。

`search_units.jsonl` は1項目1レコードです。例えば `10.1 併用禁忌` は表全体を含む1行です。
親項目のレコードへ子項目の本文を重複収録しません。子項目だけを持つ空の親項目は
`document.json` に残し、検索レコードは作りません。

各行は `unit_id`（文書キー:項目番号）、`document_key`、`kind`（section）、
`section`（code/title）、`product_yj_codes`、`text`、`source`（url）、`references` だけです。
改訂情報・原本SHA・XMLの詳細位置は `document.json` が所有します。
検索結果の改訂情報はバックエンドが文書metadataから取得します。

本文は原文順の段落とMarkdownの文脈見出しを持ちます。相互作用は3列の表、副作用は
分類・頻度・本文の表として保持します。表はHTMLで表現し、結合セルのrowspan/colspan、
セル内改行を保持します。図はファイル名・説明を本文に残します。
複数製品の項目では製品名とYJコードの見出しで各本文の適用範囲を示し、
レコードの製品コードはその項目に含まれる対象製品の集合です。

検索・引用は項目全体を返します。本文の適用範囲見出しと表の他列を併せて確認してください。
検索データの形式は `validation.json` の `search_schema_version` で
`medi-chat.pmda-sections.v2` と識別します。再生成後はSQLite検索索引も再構築してください。

`validation.json` の `pass` はXML内の参照・画像の存在と、本文の `Lang` 要素が検索単位に収録されたことを示します。XSD検証、PMDAのHTML/PDF表示との照合、臨床的な解釈の妥当性は含みません。
