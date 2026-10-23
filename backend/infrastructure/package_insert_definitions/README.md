# 添付文書の定義ソース

編集先は [package_insert_catalog.json](package_insert_catalog.json) 一つです。schema_version、意図ID、項目番号、列IDは既存の保存形式・公開契約なので維持します。

- `always_retrieved_sections` は質問内容にかかわらず取得する本文の項目です。現在は1（警告）・2（禁忌）・8（重要な基本的注意）で、配下の項目も含みます。存在しない項目を根拠として補わず、通常検索との重複はunit_idで除き、取得理由は併記します。
- `sections.<番号>.title` は正式名称の正本です。attachmentのSectionTaxonomyへ読み込み、Applicationのdefinition_projectionから各利用側へ写します。原文見出し・本文・出典・改訂をこの名称で上書きしません。親はNumberedSectionCodeから導出します。
- `display_title` / `classification_title` は用途別の別名だけを指定します。省略時は正式名称を使います。
- 意図の `sections` は検索対象の番号配列です。固定キーワードは一致した全分類を検索条件にします。keyword_priorityは列挙順を安定させるためだけに使い、分類を除外する優先順位にはしません。exclude_from_text_searchがtrueの語は除外語へ派生し、additional_stop_wordsへ重ねて定義しません。
- Jevのclassification.descriptionは説明だけを持ち、番号と名称は参照から生成します。classification.sectionsの省略時は検索対象の最初の項目です。SDK用criteriaはInfrastructureで生成します。
- 回答指示の `{section:10.1}` はApplicationで正式名称へ展開します。answer_guidance.minimum_medicinesは専用指示の薬剤数下限です。
- 相互作用列のID・名称・順はattachmentの定義です。XMLタグはPmdaXmlSettings、回答列はApplicationのAnswerPromptPolicyへ投影します。XMLの汎用タグは祖先文脈で解決します。
- 除外語・症状言い換え・見出し判定はretrievalのTextSearchPolicy、ignored_noun_suffixesはJanomeMorphologySettingsが所有します。
- 技術アダプター向けの設定dataclass（`JevClassificationSettings`、`JanomeMorphologySettings`、`PmdaXmlSettings` 等）は [definition_settings.py](definition_settings.py) が所有します。これにより `package_insert_definitions` は他のインフラアダプター（`intent` / `morphology` / `pmda_xml`）に依存せず、各アダプター側が `definition_settings.py` を参照する単方向依存をImport Linterで強制しています。

loaderはJSON IOとスキーマ・参照の検証を行い、不変な用途別モデルを組み立てます。get_package_insert_definitionsはプロセス内で共有し、JSON変更後は再起動が必要です。任意pathのload_package_insert_definitionsは独立して検証します。既定pathはこのファイル配置を基準に解決し、cwdに依存しません。

読込結果の束は `infrastructure/composition/app_lifespan.py` / `main.py` / CLI などのInfrastructure組立地点だけで展開し、サービスへはintent/text/answer/XML/Jev/Janomeの必要な用途だけを渡します。schema_models/schema_validationはこのIO境界の内部入力表現で、利用側から参照しません。encoderはdecoderが確定した原本・検索投影・source情報を使い、定義を再読込しません。

検証はリポジトリrootから行います。

```bash
uv run --project backend --locked python -c "from backend.infrastructure.package_insert_definitions.loader import get_package_insert_definitions; get_package_insert_definitions()"
pnpm test:backend
pnpm --filter backend lint
pnpm --filter backend exec uv run --locked ruff format --check .
pnpm typecheck:python
```

旧 `package_inserts.*` import、PackageInsertCatalog型、catalog引数は廃止しました。互換Facadeはありません。利用側はbackend内の所有モデルと用途別注入へ移行してください。リポジトリ外Python利用者の有無は未確認です。XML対応変更に伴う運用索引・原物の再生成は、この配置整理から自動実行しません。
