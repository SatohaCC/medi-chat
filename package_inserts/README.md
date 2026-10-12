# 添付文書の共通カタログ

定義の編集先は [package_insert_catalog.json](package_insert_catalog.json) です。`backend` の検索・XML変換 が同じファイルを読み込みます。Python標準ライブラリのみで動作します。

| JSONの項目 | 管理する内容 |
| --- | --- |
| `sections` | 番号、正式名称、用途に応じた名称、XMLタグと文脈依存タグ |
| `intents` | 質問意図、検索対象、キーワード、優先順位、Jev分類の説明、意図別の回答指示 |
| `fallback_intent` / `general_intent` | 通常検索とJevの対象外判定に使う意図ID |
| `text_search` | 追加の除外語、名詞の接尾辞、症状の言い換え、見出しだけの検索単位 |
| `interaction_columns` | 構造化データの列ID、XMLタグ、回答で使用する列名と表示順 |
| `xml` | 文書メタデータのタグ、参照タグ、検索単位へ変換するタグ |
| `answer_prompt` | 引用例の項目参照、複合質問の回答指示 |

## 参照と派生規則

- 項目の正式名称は `sections.<番号>.title` に一度だけ定義します。親項目は番号から解決します。
- 意図の `sections` は実際に検索する項目番号の配列です。子項目や関連項目も明示します。表示名は最初の項目から取得します。
- `display_title` と `classification_title` は意図的に名称を短縮・言い換える場合だけ指定します。省略時は `title` を使います。
- Jevの `classification.description` は質問の説明だけを記述します。番号と名称は参照から生成します。`classification.sections` の省略時は検索対象の最初の項目を使います。Jevに提示しない意図は `classification` を省略します。
- 固定キーワードは `keyword_priority` の小さい意図から照合し、最初の一致を採用します。JSON内の並び替えで判定順は変わりません。
- キーワードの `exclude_from_text_search` が `true` の場合、同じ語を形態素検索の除外語に含めます。この語を `additional_stop_words` に重ねて書くと検証エラーになります。
- プロンプトの専用指示は `{section:10.1}` の形式で正式名称を参照します。番号や項目名を文章に再定義しません。`answer_guidance.minimum_medicines` は専用指示を適用する薬剤数の下限です。
- 原文の見出し、本文、出典、改訂、薬剤情報は構造化データから使います。カタログの名称で原文を上書きしません。
- XMLの汎用タグは `xml_contexts` に祖先タグとともに指定します。見出しの出現順から番号を推測しません。

列ID、意図ID、項目番号はAPI・構造化データの識別子でもあります。既存IDの変更は利用側の契約変更になるため、名称変更は名称フィールドで行います。XML対応や構造化列の変更後は、構造化データと検索索引を再生成します。

## ファイルの責務

- `catalog_loader.py`: JSONの読込と検証。重複キー、未知フィールド、型違い、未定義参照、キーワード優先順位やXMLタグの衝突を検出します。
- `catalog_models.py`: 不変モデルと用途別の辞書・表示文の生成。
- `text_formatting.py`: 項目番号順の比較キー、スコープ見出しの整形。

`get_package_insert_catalog()` は読込結果をプロセス内で一度だけ保持します。JSONを変更したら実行中のプロセスを再起動してください。`load_package_insert_catalog(path)` は別ファイルを検証する場合に使います。カタログはアプリ生成時とXML変換開始時に検証されます。

## 検証

リポジトリのルートで定義だけを検証できます。

```bash
python -c "from package_inserts.catalog_loader import get_package_insert_catalog; get_package_insert_catalog()"
```

バックエンドのテスト環境で `backend/tests/test_package_insert_catalog.py` を実行すると、カタログだけの変更が検索・Jev・プロンプト・XML変換に反映されることも確認できます。RuffとPyrightの対象に共通パッケージを含めています。

今回の集約では、既存の検索対象・固定キーワード優先順位・除外語・Jev選択肢・XML変換結果を維持しています。複合質問のプロンプト内の項目名は正式名称へ統一し、検索定義だけに存在していた意図の表示名も項目から生成します。
