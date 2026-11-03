# 品質コマンドと証跡

## 共通の実行入口

エージェント共通の変更範囲検査は`pnpm agent:check`、全体手動検査は`pnpm quality`を入口にする。側別は`pnpm quality:backend`・`pnpm quality:frontend`・`pnpm quality:scripts`。実行前に`--list`で対象コマンドを確認できる。構成と各エージェントHook adapterは[scripts/README](../../scripts/README.md)を参照する。

この入口はソースを自動修正しない。通常のbackendテストから実DB・非公開原本を必要とするテストを除き、frontendはNodeの単体テストを実行する。実PostgreSQL・ブラウザ・外部APIの検証は別に選択し、共通コマンドの成功で代替しない。

開発中のquick検査は早期フィードバック、完了時のfull検査は受入判断に使う。モデルへの信頼で最終検査を省略しない。quickの頻度や範囲を変える場合は、同じ受入条件と検証範囲を保った代表的な作業で、変更前後の反復数・総所要時間・修正前に検出した不具合・最終結果を比較する。単一実行の時間やモデル名だけから検査を削らない。fullの最終ゲートと受入条件は頻度変更後も維持し、テスト結果だけで仕様網羅を証明したとは扱わない。[検査頻度とコストの背景](harness-strengthening-plan.md#調査文書を適用する際の留保)

受入条件がある作業では、[仕様JSONの例](quality-task.example.json)に従って要件ID・受入条件・対応テストを定義し、`--spec <JSON>`で選択する。作業用`tmp/quality/task.json`は手動・hooks共通で自動読込する。通常の回帰検査も維持する。登録可能なテスト、integrationの明示選択、受入検査の未実施判定、修正フィードバック・停滞停止は[scripts/README](../../scripts/README.md#仕様に基づくテスト選択)を正本とする。自然言語の仕様からテスト内容の妥当性まで自動判定するものではない。

pytestの設定はルート`pytest.ini`で共有する。`pytest`と`python -m pytest`のどちらからもbackendとscriptsをimportできる。`testpaths`は`backend/tests`と`scripts/hooks`で、backend用のDB隔離・マーカー選別は既存の`backend/tests/conftest.py`が担当する。

frontendのソースは`.gitattributes`とBiomeでLFに統一する。`e2e/fixtures`・`e2e-real/fixtures`は原本のバイト列を保持するため、改行変換と整形を行わない。TypeScript 7のCLIは`@typescript/native`、StyleX ESLintが使うコンパイラーAPIは`typescript`名の`@typescript/typescript6`で供給する。`pnpm typecheck:frontend`の`tsc`は引き続き7系を実行する。

以下はリポジトリルートからのコマンド。実行前に対象のpackage.jsonと環境を確認し、現在の差分と承認済み計画に必要な検証を選ぶ。
backendの依存はuv.lockで管理し、pnpmのbackendスクリプトはuv経由で実行する。backendにはPython 3.14以上と対象パッケージのdev依存が必要。通常のローカルpytestは実DB試験を除外し、DB接続・dotenv・認証情報を隔離する。実PostgreSQLはGitHub Actionsの`pnpm test:postgres`で検証する。サービス・データ・外部APIキーが必要な検証は前提を明示し、未設定による代替応答やskip・deselectedを成功としない。

pnpm-workspaceの`python.enabled=false`でpnpmの別Python環境管理を停止し、Python依存はbackendのuv.lockへ一本化する。backend/pylock.tomlはuv exportの標準形式を保持する。Node依存はルートで`pnpm install --frozen-lockfile`を実行する。一時snapshotの共有node_modulesからpackage managerを実行しない。型検査の比較にはルートの実在Pyrightを直接Nodeで起動して`--project <比較対象config>`を指定できる。

## テスト設計

- 配置は[backendのテスト分類](../architecture/backend-design.md)と、対象パッケージの既存テストを正本にする。frontendのNodeテストはfrontend節を参照し、追加時は対象範囲の既存配置・実行方法に合わせる。
- 期待結果は要件と公開契約から導き、実装の判定式をコピーしない。Domainモデルは実オブジェクトを使い、外部SDK・通信には適切な既存ダブルを使う。
- 新規・移動したコードが型・lint・テストの実行対象に入ることを設定と共通入口で確認する。検査対象や入口の変更では隔離した負例で検出能力も確認し、対象外のパスを検査済みと報告しない。
- Reader/Publisher等の契約分離では、テストが実際に使う組立関数と注入先・公開署名を確認する。DB不要の配線検査と実PostgreSQLの検証を分け、importの更新だけで完了しない。
- 固定hashの試験はbytes自体の契約か、改行差を許すテキスト内容の契約かを先に決める。後者で正規化する場合はLF/CRLFの両方が通り、内容変更は失敗することを確認する。原本・署名対象・バイナリには改行正規化を適用しない。
- feature-pipelineを使用中のケースと実テストの対応、Fixture/Fakeの変更による仕様差し戻しは[Skill](../../.agents/skills/feature-pipeline/SKILL.md)の規約に従う。参照だけでパイプラインを開始しない。
- カタログ/XML変換では[定義ソース](../../backend/infrastructure/package_insert_definitions/README.md)と対象テストを確認し、本書の原本照合規則に従って内容・文脈の保持を検証する。

## 実行条件と資源の検証

### 検査対象と失敗の切り分け

新規・移動パスや共通入口の検出能力は本書の「テスト設計」に従って確認する。失敗した場合はchained exceptionまで読み、業務期待値に達した失敗か、その前の設定・IO・証跡保存の失敗かを区別する。テスト所有の一時領域を使い、必要なら同じfixture・環境で変更前と比較する。PermissionErrorを一律に環境原因とせず、再実行成功で初回失敗や未確定原因を消さない。

独立したE2E実行を並行させる場合は、outputDir・port・build出力を実行ごとに分ける。分離できなければ直列実行する。同一実行内のworker並列化と区別し、証跡保存の競合を製品退行と断定しない。標準mock/realの実行先は下のfrontend節を正本とする。

性能やnative eventの測定では、ready後の実process PIDと起動processの親子・所有関係を確認し、同じ実processからbaselineと測定値を取る。launcher PIDだけで計測欠落を製品不具合と判定しない。停止するのは試験所有と確認したprocessだけにする。

### 通常起動・認証・監視

必須設定・認証応答・DB revisionを変更するときは、テスト用設定だけでなく通常設定とCIのHTTP/WS/OS経路を確認する。秘密値を表示せず、必須キーの有無・接続先の所有範囲・revisionを調べ、frontend節にある既存configured gateで実起動とread-only healthを検証する。設定/DBの変更は依頼範囲に従い、確認のために運用データを自動更新しない。

認証応答を読む開発監視・fixtureも追跡し、期待された認証拒否と未知の応答・通信途絶を分けて確認する。監視の回帰試験では、子processが異常時の停止判定まで生存する条件で、誤再起動を検出できることを確認する。

### 依存環境の所有範囲

interpreter更新や仮想環境の再構築前に、.venv等のlink/reparse point・実target・所有範囲を確認する。共有ストアをプロジェクト専用ディレクトリとして削除・移動しない。専用環境は対象lockで生成し、既存の共有資源や担当外の環境を保持する。通常の専用ディレクトリへ一律の退避・並行環境を要求しない。

### CI・配置先の実行条件

runtime/version指定を変える場合は、配置先builderのruntime選択と、その後のuv等による依存同期を両方確認する。ローカルに特定interpreterがある環境の成功を、配置先での解決成功に置き換えない。採用版でのローカル品質結果と、対象コミットのCI/Preview結果を分けて記録する。

Workflow APIを変える場合は、実際の認証主体と必要な権限を確認し、不要な管理APIを増やさない。マージ等の変更を伴わない同じ読取APIをWorkflowの実トークンで検証し、模擬応答による分岐検証と区別する。管理者gh認証での成功をGITHUB_TOKEN権限の証明にせず、管理者バイパスを追加しない。ローカル検証だけでは実マージ成功を報告しない。

## Python

| 対象 | 読み取り専用の検証 |
|---|---|
| backendテスト | `pnpm test:backend`、限定時は`pnpm --filter backend exec pytest tests/<対象>.py` |
| 実PostgreSQL（CI） | `pnpm test:postgres`（`postgres and not source_data`。接続設定不足は失敗） |
| backendlint | `pnpm --filter backend lint` |
| Domainハーネス | `pnpm --filter backend lint:domain`、検出能力の回帰は`pnpm --filter backend lint:domain:harness` |
| backendformat確認 | `pnpm --filter backend exec ruff format --check .` |
| Python型検査（Pyright） | `pnpm typecheck:python` |

通常pytestはDB不要テストを実行する。`pg_engines`への直接・間接依存はpostgresへ分類される。fixtureを使わず実DBへ接続する試験は`@pytest.mark.postgres`、Git管理外の原本・生成物を使う試験は`@pytest.mark.source_data`を付ける。CIはsource_dataを除外し、実DBの設定不足をskipへ置き換えない。

`pnpm typecheck:python`はbackendのPyright・mypyと、`pnpm typecheck:scripts`による`scripts/`のPyright・mypyを順に実行する。`pnpm quality:scripts`も開発ツールの型検査を実行する。ルートのpyrightconfigの既定includeはbackendであり、scripts単独検査ではCLI引数で対象を明示する。一部だけの成功を全体成功として扱わない。
カタログだけの検証は`python -c "from backend.infrastructure.package_insert_definitions.assembly import get_package_insert_definitions; get_package_insert_definitions()"`。実行環境を確認し、これだけで検索・プロンプト・XML経路が検証できたと扱わない。

## frontend

| 層 | 読み取り専用の検証 |
|---|---|
| lint | `pnpm --filter frontend lint` |
| lintとformat確認 | `pnpm --filter frontend exec biome check .` |
| 型 | `pnpm typecheck:frontend` |
| ビルド | `pnpm build` |
| 接続ヘルパー単体 | `node --experimental-strip-types --test frontend/features/chat/api/chatWebSocket.test.mjs`（対応するNodeが必要） |
| チャット画面（Playwright / Chromium） | 初回は`pnpm --filter frontend exec playwright install chromium`、実行は`pnpm test:e2e` |

### frontend変更時の確認

- チャット変更ではREST/WebSocketの契約、切断・再接続、進行中の回答と次の送信履歴への影響を対象範囲に応じて確認する。
- 根拠表示や描画を変える場合は、原本・現行登録形式から読取り・実コンポーネントまで、変更箇所を実際に通る経路を確認する。人工fixtureや別形式の描画成功を、保存済みデータやユーザーの実行中ページの成功へ置き換えない。
- StyleX等のCSSを変える場合は、必要な実Next.jsのdevelopment・HMR・production経路で生成CSSとcomputed styleを確認する。生成クラス・型・build・独立ハーネスの成功だけでは実アプリへの装飾適用を判定しない。記録時の版のPostCSS順や特定のshorthand対策を、原因未確認の別環境へ機械適用しない。
- 型・lint・ビルド、接続ヘルパーの単体テスト、ブラウザと実サーバー接続は別の検証層として記録する。configured起動、mock、実接続の経路と資源分離は下記の契約に従う。

ルート`pnpm test`はbackend（旧data_toolsテスト移行済み）であり、frontendのNodeテストを含まない。ブラウザ・実サーバー接続も別に確認する。
`pnpm test:e2e`は通常devのdotenvと設定解決を保持し、configured PostgreSQLのread-only readiness→実`backend.main:app` OS health（3212）→モックChromium→実接続Chromiumの順に検証する。どの必須層の非0も全体非0とし、未準備/staleをfresh fixture成功で代替しない。configured要求はhealthだけで、DBの自動更新・LLM質問・Web保存をしない。占有portは拒否し、試験所有processだけを終了する。
モック層はチャット画面とイベントを検証する。実接続層は一時DB・実backendを使い、外部LLM/検出SDKの固定ダブルは実通信として扱わない。

明示的な単独実行は`pnpm --filter frontend test:e2e:mock`/`test:e2e:real`。実接続は専用Next/backendと専用test DBの所有UUID schemaを使い、APIをinterceptせず、登録・同YJ置換・一部旧版保持・参照0旧payload削除・同原本再送の非復活・OS再起動後GET/候補/検索の維持を検証する。更新対象の一時DBと、変更してはいけない運用DB/原物/backupを区別する。現行形式のfixtureは空DBへのAlembicと原本からの登録で作成し、旧索引の移行・stamp・互換読み取りを行わない。実接続試験では外部LLM keysを空・dotenv無効にし、configured smokeへ漏らさない。Next試験出力は`.next-e2e-mock`/`.next-e2e-real`（必要時buildは`.next-e2e-build`）で通常`.next`と分離する。

## 原本XML・添付文書の検証規則（内容・文脈保持と許容される表示形式差）

PMDA XML原本から添付文書データへの変換・照合（Oracle検証）では、原文の内容と文脈が完全に保持されていることを必須としつつ、以下の既存の表示形式差を許容される表現として判定規則に明記する。

1. **ブロック順序の緩和（兄弟Detail要素の先行結合）**:
   - 項目 13, 16.1, 16.6, 17.1 などにおいて、親要素に属する兄弟 Detail 要素が介在する表・図・リスト・脚注より前に結合されて段落化される（例: 16.1 で日本人志願者Detail→図→日本人表→脚注→外国人志願者Detailが、日本人+外国人統合段落→図→日本人表→脚注→外国人表となる等）。
   - すべての散文（prose）値が完全であり、親・治験・適応症の文脈が保持されている場合は、原本出現順からの並び替えを許容される既存表現とする。
2. **生成される文脈ラベル・強調段落・山括弧表現**:
   - 原本見出し（Headers）や一部の親Detailは、文脈ラベルや生成された強調段落（`<strong>`等）として展開される（項目 1, 2, 4, 7, 8, 9.2, 9.7, 16.2等）。
   - 同一のItem/Header文脈に対応する見出し反復（例: 16.1における複数の`〈単回投与〉`生成）や、既存山括弧の重複（`〈`の二重化等）は生成表示形式として扱い、余分な生XMLノードの混入と誤認しない。
3. **図（Graphic / Figure）の空段落レンダリング**:
   - 項目 16.1 および 19 などの図要素は、`figure.reference` にファイル名（例: fig05, fig06）を保持するが、HTMLレンダリングでは空段落 `<p></p>` として出力され、画像バイナリやファイル名文字列はHTML本文に現れない。
   - 性状 3.2 の InlineGraphic もプレースホルダと原本順を保持していれば、HTML本文上の空段落表現を許容する。
4. **表の `td` 出力とアクセシビリティヘッダー（`th` / `scope`）の非付与**:
   - 表（SimpleTable等）はすべて `<td>` で出力され、`<th>` や `scope` 属性を持たない。原本のヘッダー構造・グリッド・ペイロード列がセルテキストとして保持されている場合、HTML上の `th`/`scope` の欠如を既存表現として受容する。原本に指定がない限り `th`/`scope` を捏造しない。
   - 相互作用・副作用の生成列タイトルはペイロード列に存在するが、表示ヘッダーセルではない。
5. **参照（Reference）の集約レベル**:
   - 相互作用 10.1 および 10.2 の参照は、セル単位ではなく表/ブロック単位に集約され、原本の出現順・対象が表参照として保持される（SimpleTableのセル参照はセル単位で保持）。この集約レベルの差を許容する。
6. **グループ化段落内での参照重複排除**:
   - グループ化された段落内における同一参照の重複は、初出の順序を保持した上で重複排除される（例: 16.1 で 6 件 → 5 件、16.7 で 25 件 → 22 件）。出現件数の絶対一致ではなく、グループ化された意味論として許容する。

## 自動修正と最終確認

ルートと各パッケージの`check`は`--write`/`--fix`やformatを含む。Evaluatorでは使わない。書き込み役も担当外の本番・テスト・既存差分を変更しないよう対象を限定し、実際の差分を確認する。
反復中は関連するテスト、全ケース後は計画とプロジェクトに必要な品質ゲートを実行する。現在の差分に有効な証跡は再利用できる。コマンド・場所・終了コード・件数・差分版を記録し、環境エラー・未実施・skip/xfailは区別する。
この資料にコマンドがあること自体は、実行成功の証跡ではない。
