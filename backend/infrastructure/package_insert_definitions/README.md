# 添付文書の型付き定義と技術設定

定義はPythonの不変クラスで管理します。添付文書の構造、取得方針、技術設定をそれぞれの所有層に置き、名称・意味・対応表を利用側へ複製しません。

| 編集する内容 | 正本 |
| --- | --- |
| 項目番号・正式名称・階層・内容の範囲、相互作用列のID・名称・順序 | [DomainのSectionDefinition / SectionTaxonomy](../../domain/attachment/value_objects.py) |
| 常時参照する項目、質問意図と検索項目、固定キーワード、除外語・症状言い換え、分類用の対応 | [Applicationの検索方針](../../application/retrieval/policies/standard.py) |
| 回答用の指示、引用項目、表示への投影 | [Applicationの回答方針](../../application/chat/policies/standard.py) |
| XMLタグ・祖先文脈・列タグ、Janomeの技術設定 | [XML・形態素設定](xml_settings.py) |
| Domainの項目の意味からJev選択肢への変換 | [Jevへの投影](jev_settings.py) |

[assembly.py](assembly.py) は型付き定義を用途別に組み立てるだけです。`get_package_insert_definitions()` の束はComposition RootやCLIで展開し、各サービスには必要な型を注入します。定義を差し替える場合は、`dataclasses.replace` や各型のコンストラクタで新しい値を作り、`build_package_insert_definitions()` または各投影関数へ渡します。旧JSON読込・任意pathの設定読込は廃止しました。

常時参照は `EvidenceRetrievalPolicy` が所有し、質問の `IntentPolicy` とは独立しています。現在は1・2・8とその配下を対象に、記載がある本文だけを取得します。取得方針を変えても質問意図の定義は変わりません。

正式名称・項目の意味と、文書に記載された原文見出し・本文・出典・改訂情報を区別します。名称の定義を変えても原文を上書きしません。親項目は `NumberedSectionCode` から導出し、重複・親不在はDomain、存在しない項目への参照は組立時に拒否します。Jevには質問選択用の対応から項目番号・名称・意味を投影し、XML側にはタグに対応する項目番号・名称を投影します。

ガイド画面のJSONは編集元ではなく、Python定義から生成した表示成果物です。定義を変更したら次を実行し、生成差分を確認してください。Next.jsのビルドはコミット済み成果物を使用し、Python実行環境を要求しません。CIはPython定義と表示成果物の一致を検証します。

```bash
uv run --project backend --locked python -m backend.infrastructure.cli.export_search_guide
uv run --project backend --locked python -m backend.infrastructure.cli.export_search_guide --check
pnpm test:backend
pnpm --filter backend lint
pnpm typecheck:python
```

Jevの判定方式・閾値・説明の調整は、この配置変更とは分けて評価します。クラスへの移行だけで実Jevの精度向上を確認したとは扱いません。


## SectionScopeの編集根拠

全54項目の`SectionScope`は必須です。空の説明はPrimitiveで拒否します。
項目名・親子関係・具体的な構成要素は、リポジトリの次の資料に照合しています。

- `reference/電子添文XMLデータ/（別添4）入力項目一覧.xlsx`：Sheet1の72～265行。組成75～103行、性状104～143行、相互作用160～183行、副作用184～203行、薬物動態214～222行、臨床成績223～226行、理化学的知見233～247行。
- 同ディレクトリの`（別添3）データモデル.xlsx`：項目階層と構成要素。
- 同ディレクトリの別添1 XMLスキーマと別添2テンプレートインスタンス：タグと項目の対応。

Scopeは資料の引用文ではなく、項目の意味を説明する要約です。構造資料に詳細な臨床的定義がない項目は、名称と階層に沿った説明に留めます。説明中の具体例は記載範囲を理解するためのもので、すべての製品にその情報があることを保証しません。貯法・有効期間は入力項目一覧30～32行の文書基本情報であり、20項への掲載を前提にしません。製剤の性状だけから粉砕可否を判断する説明もしません。

Jevの選択肢には、対応する全項目と配下の項目の名称・Scopeを重複なく投影します。4/5、6/7のような統合した選択肢でも先頭以外のScopeを含めます。分類の選択肢ID・数、取得対象、閾値は変更しません。実Jevの精度への効果は実通信を用いた別途評価が必要です。
