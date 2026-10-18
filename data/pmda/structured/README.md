# PMDA電子添文の構造化データ

原本XMLを変更せず、バックエンドの変換器から現在形式を生成する。

```powershell
uv run --project backend --locked python -m backend.infrastructure.cli.structure_pmda_xml --source-dir data/pmda/originals --output-dir tmp/pmda-current/structured
```

| ファイル | 用途 |
| --- | --- |
| `document.json` | `medi-chat.pmda-prescription-xml.v2`。大項目ごとに保存し、子項目を `children` に保持する。原文ツリー・XMLパス・属性・改訂・表・参照も保持する。 |
| `search_units.jsonl` | `medi-chat.pmda-sections.v4`。大項目ごとに1行。ブロックの `context.section` に元の項目番号・標準名を保持する。 |
| `validation.json` | 原文本文の収録範囲、番号・参照・画像の検査結果。XSD検証とは別の検査。 |

10は10.1・10.2を配下に持つ1件として作成する。原文のHeaderがなければ補わない。`title` は標準項目名で、原文見出しとは別の情報である。汎用表の先頭行はセルのまま保持し、列見出しへ昇格させない。

旧JSON・旧検索データは受け付けない。旧SQLite移行機能も提供しない。原本から新しい出力先へ再生成し、空のDBにAlembicでスキーマを作成して初期登録する。既存データを自動上書きしない。

詳細は[変換規則](../../../docs/pmda-xml-conversion.md)と[バックエンドの運用手順](../../../backend/README.md)を参照。
