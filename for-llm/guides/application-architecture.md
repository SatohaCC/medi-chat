# Applicationの配置・公開範囲・importハーネス

Feature-first、Command/Query分離、Single-File Sliceを基本とする。実行時の振る舞いを変更するCQRS基盤やジョブキューの導入は、この配置ルールには含めない。

## 配置

```text
application/<feature>/
  commands/<use_case>.py       # 更新ユースケース。専用入力・handler・結果を同居
  commands/services/<task>.py  # 更新側の共有処理。必要なときだけ作る
  commands/models.py          # 更新側の処理状態・結果。参照側と共有しない
  commands/dtos/<meaning>.py   # 更新側だけで共有するDTO。必要な場合のみ
  commands/policies/<policy>.py
  queries/<use_case>.py        # 参照ユースケース。専用入力・handler・DTOを同居
  queries/services/<task>.py   # 参照側の共有処理
  queries/dtos/<meaning>.py    # 複数Queryで共有する表示DTO
  queries/models.py           # 参照側の検索条件・投影・処理中モデル
  queries/policies/<policy>.py
  interfaces/<capability>.py   # 外部契約（Protocol）。参照系は*_query_reader.pyまたは*_reader.py
  values.py                   # ID・入力値等。DTOは置かない
  policies.py                 # 両側のDTOに依存しないApplicationの判断
  policies/<policy>.py
  errors.py
```

必要な役割だけを置く。Serviceが1つでも側ごとのservices/へ置く。Feature直下のservices/・service.py・services.py・ports/・models.py・dtos/は認めず、更新と参照を束ねるFacadeも設けない。

Command/Query/Resultクラスの一律必須化や行数による分割はしない。Pythonでは1ユースケースを1ファイルにまとめる。`commands/create_order/handler.py`の階層や`commands/handler.py`等の汎用名は使わない。Feature共通のDTOを導入せず、共用が必要な参照DTOはqueries/dtos/に閉じる。common/はFeatureに依存しない値・例外と、参照専用の汎用DTOだけを置く。

## 依存と公開範囲

- Applicationのimportはbackendから始める絶対import。wildcard・動的importは禁止し、__init__.pyは空またはdocstringのみ。
- Applicationは標準ライブラリ・Application・Domainに依存する。SQL・SDK・ファイル操作・スレッド等の実装はInfrastructureに置く。
- commands/とqueries/の間では、Handler・Reader・DTO・モデル・補助Serviceを相互にimportしない。別Featureでも同じ。commonの参照DTOもCommandから使わない。
- Handler同士を直接呼ばない。側ごとに共有する処理はcommands/services/またはqueries/services/へ切り出す。補助ServiceからHandlerへの依存も禁止する。
- 集約のRepository契約はdomain/<feature>/repositories.py、実装はInfrastructure。Query側と側に属さない共通方針からRepository契約へ依存しない。Commandで更新対象の集約を読むことは許可する。
- QueryReaderはinterfaces/<subject>_query_reader.pyに置き、参照側のDTO・モデル・値を返す。SQLやORM射影はInfrastructureが実装し、Query Handlerはその契約に依存する。
- Commandの再送結果取得は更新操作の冪等性を担う専用契約とCommand結果を使い、表示用QueryReader/DTOを流用しない。Repositoryが必要かはDomain集約の取得・保存という責務で判断し、DBアクセスだけを理由にDomainへ移さない。
- 各側のHandlerは同じ側のservices/interfaces/readers/models/dtos/policiesと共通の値・例外・純粋な方針に依存できる。modelsは値、DTOは同じ側のmodels/DTO、interfaces/readersは同じ側のmodels/DTO/契約に依存する。DTOからReader/Handlerには依存しない。
- 外部契約はFeature直下のinterfaces/に一本化する。更新契約・外部連携・実行制御・参照契約（QueryReader）を集約し、参照契約は*_query_reader.pyまたは*_reader.pyと命名する。
- Feature間はbackend/application-architecture.tomlのdepends_onとpublic_modulesを両方満たす必要がある。宣言およびモジュール間の循環は禁止する。
- Presentationは公開されたcommands/queriesとDTO・モデル・例外を利用する。Reader・内部Service・方針・値・外部契約への依存は禁止し、具象の配線はComposition Rootが行う。
- 型専用・関数内・別名・package形式のimportも検査する。TYPE_CHECKINGや関数内importで規則を迂回できない。

Queryは集約の復元を必須としない。DomainのID・値を利用することと、更新用Repositoryを利用することは区別する。認可・入力検証は参照側にも必要。SQLのJOINはInfrastructure内で許可する。

Domain上の不変条件、契約の責務、Queryが状態を更新しないこと、同一内容を複製したDTOの意味はレビューと振る舞いのテストでも確認する。AST検査だけで任意の実行時動作やDTOの意味的一致を完全には証明しない。

## 実行と終了コード

```bash
# 全規則の診断。未移行コードも指摘し、違反があれば1で終了
python scripts/application_architecture.py
python scripts/application_architecture.py --feature attachment_import
python scripts/application_architecture.py --json

# 標準Lint/CIもこの全規則コマンドを実行
python scripts/application_architecture.py

# 他プロジェクトへの段階導入時だけ対象を限定して確認
python scripts/application_architecture.py --phase enforced

# import規則だけを確認する場合
python scripts/application_architecture.py --phase imports

# 正常例・違反例・CLI契約・現行importの回帰検査
python -m pytest backend/tests/architecture/test_application_harness.py -q
```

rootはスクリプト配置から解決し、cwdに依存しない。`--root`/`--config`で独立したコード例にも適用できる。終了コードは0=対象規則で違反なし、1=違反あり、2=設定・入力エラー。診断対象のコードはimport・実行しない。

`pnpm --filter backend lint`とCIは全規則を強制する。`lint:application:audit`も同じ全規則の診断となる。全Featureが移行済みで、`enforced_features`も全Featureを列挙する。imports/enforcedの限定実行は移行支援用であり、限定実行の成功を全規則適合と報告しない。既存のImport Linter・アーキテクチャ検査は維持する。

| ID | 検査 |
| --- | --- |
| APP000 | Python構文エラー |
| APP001 | Feature宣言・配置・汎用ファイル名 |
| APP002 | 相対import |
| APP003 | wildcard import |
| APP004 | package再公開・初期化処理 |
| APP005 | 外層・非標準ライブラリへの依存 |
| APP006 | 同Featureの役割間依存 |
| APP007 | ユースケース間の直接import |
| APP008 | Feature間依存と公開モジュール |
| APP009 | commonからFeature/Domainへの依存 |
| APP010 | 具体的なI/O・実行基盤のimport |
| APP011 | 動的import |
| APP012 | 同Feature内のモジュール循環 |
| APP013 | Presentationから内部契約・Reader・方針・値・共有Serviceへの依存 |
| APP014 | Command／Query間のHandler・Reader・DTO・モデル共有 |
| APP015 | Query側・中立モジュールからDomain Repositoryへの依存 |

## 段階的移行の記録

2026-10-24時点のApplication内部に対する初回診断は183件（配置45、Feature境界41、相対import97）。正常例・禁止例のテストを先に通した後、相対import97件だけを絶対importへ移行した。配置や業務フローはこの段階では動かしていない。

| Feature | 全規則の残件 | 状態 |
| --- | ---: | --- |
| attachment_import | 0 | 取り込み・登録結果の再送を所有 |
| file_upload | 0 | 転送・一時保存を所有 |
| medicine | 0 | カタログquery、照合policy、参照Handlerへ整理 |
| indexing | 0 | 不変モデル・値・投影command/policyへ整理 |
| retrieval | 0 | 根拠取得query、判定service、選択policy、ポートへ整理 |
| chat | 0 | 回答command、準備/生成service、prompt policy、参照Handlerへ整理 |

全規則の指摘は172 → 133 → 0件となった。標準Lint/CIを全規則へ昇格済み。例外・違反baselineは追加していない。ポート合成と共有サービスの規則を実例で精査し、許可例・禁止例と循環検出の合成テストを追加してから適用した。

公開モジュールの宣言先が実在すること、全Featureが移行対象であること、実リポジトリが全規則を満たすこともテストで強制する。配置を通すための互換再公開・旧ファイル・並行APIは残さない。必要な共有出力型・ポート・方針だけを公開し、ユースケース固有のhelperは公開しない。

## CQRS境界への移行

2026-10-24に、先にハーネスの禁止例・許可例55件を検証し、旧配置26件を診断してから本番の配置を移行した。移行後に取り込みのCommandとQueryの共有依存14件を検出し、更新専用の再送契約ImportReplayと参照用ImportQueryReader/ImportDetailへ分離した。指摘を無視する例外やbaselineは増やしていない。

添付文書取り込みはAttachmentImportCommandsとImportHistoryQueriesを別々に注入し、Executorの寿命はComposition Rootが所有する。医薬品カタログはMedicineQueriesが直接実行する。チャット・根拠検索・索引用の純粋な投影は永続状態を変更しないため参照側とする。索引のDB更新自体はInfrastructureの登録トランザクションが担当する。
