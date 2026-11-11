# 開発ツールと品質検査

テスト本体とlint・型検査設定は`backend/`・`frontend/`が所有する。全エージェントが利用する共有CLIは`pnpm agent:check`で、実行計画は`checks/quality.mjs`が所有する。手動・CI・各エージェントのHook adapterはこのCLIから同じパッケージ検査を呼べる。

| 場所 | 責務 |
| --- | --- |
| `checks/` | 品質検査の実行とApplication・Domainの構造検査 |
| `hooks/` | Codexイベントの解析、編集ファイル判定、整形、検査結果の返却と重複実行防止 |
| `postgres/` | PostgreSQLの初期化 |
| 直下のスクリプト | 環境解決、生成データの出力、開発ログ設定 |

## 開発バックエンドのログ

`pnpm dev:backend`は`uvicorn --reload`を直接起動し、stdout/stderrをコンソールへ表示する。アクセスログのクエリは`uvicorn-dev-logging.json`のフィルタで`?[REDACTED]`へ伏せる。ログ本文や例外の内容を共有する前に確認し、患者情報を含む原文を外部へ貼り付けない。

ログはコンソールへ出力し、セッションログのファイル保存・自動再起動・稼働ログ検査は持たない。`pnpm dev`で別起動するfrontendのログは対象外。共通品質検査は開発サーバーの稼働ログに依存しない。

## 共通コマンド

ルートから実行する。いずれも検査対象のソースを自動修正しない。

```sh
pnpm quality                  # backend・frontend・開発ツール
pnpm quality:backend
pnpm quality:frontend
pnpm quality:scripts
pnpm typecheck:scripts        # 開発ツールのPyright・mypy
pnpm quality:changed          # HEADとの差分と未追跡ファイルから選択
pnpm quality:changed --phase quick
pnpm quality:changed --list   # 実行計画だけ表示
pnpm quality:scripts --report tmp/quality-scripts.json # 機械可読な結果も保存（親ディレクトリは事前作成）
pnpm agent:check --phase quick # エージェント共通の変更範囲検査
pnpm agent:check --report tmp/quality/result.json # 完了前の検査と構造化レポート
node scripts/checks/harness-metrics.mjs # Hook実行時間・差し戻し率・ループ警告・管理オーバーヘッドの集計
node scripts/checks/verify-clean-checkout.mjs --ref <commit> # 指定commitを隔離worktreeで再検証
```

`full`は対象側のlint・format確認・型検査・単体テストを実行し、backendでは構造検査も含む。`scripts`ではツールの回帰と生成物の整合性も検査する。`quick`はlint・実行入口の構文確認に加え、backendではプロジェクトのMypyを`-p backend`で実行する。失敗・起動不能・タイムアウトは非0で終了し、他の検査も続けて結果を表示する。一時ファイルはプロジェクト内のGit管理外領域を使い、uv cacheは`UV_CACHE_DIR`指定時にその場所、未指定時に`.uv-cache`を使う。

実PostgreSQL契約・ブラウザ・外部APIは変更パスだけから自動選択しない。backendの通常起動確認は`agent:check`・`quality:changed`のfullでbackend scopeがある場合に自動選択する。quickや`quality:backend`など個別計画では、通常設定の起動確認を下の仕様JSONで明示選択できる。必要な前提は[検証手順](../docs/development/validation.md)を参照する。CIは共通のbackend・frontend・scripts検査に加え、実PostgreSQL契約を実行する。

`--report <path>`は実行前に全検査を`not_run`として保存し、各検査後に状態・終了コード・所要時間・コマンドを更新する。状態は`passed`・`failed`・`start_error`・`timeout`・`incomplete`・`not_run`。taskに追加runtimeがあれば`runtimes`へ記録する。空の実行計画は終了コード0でもレポートでは`not_run`とする。通常の回帰検査の`passed`はコマンドの正常終了を示す。仕様から追加した受入検査は後述の成功件数とskipも確認する。未選択のbackend起動・実DB・source_data・ブラウザ・外部APIは`excludedLayers`に記録する。選択しただけの層を検証成功と扱わず、各taskの状態を確認する。

## 仕様に基づくテスト選択

作業の受入条件を[仕様JSONの例](../docs/development/quality-task.example.json)の形式でテストへ対応付ける。`version: 1`、作業を示す`task`、要件ごとの一意な`id`・`acceptance`・空でない`checks`が必須。自然言語からテストの意味を推測する仕組みではなく、対応付けの妥当性は仕様レビューで確認する。

- `kind: python`は`backend/tests/`または`scripts/hooks/`の既存テストを選ぶ。任意の`test`にpytestの関数・クラス・`TestClass::test_method`を指定できる。実DB・非公開原本のマーカーは除外されるため、それらが必要なら通常のunit指定で代替しない。
- `kind: node`は`frontend/features/`・`frontend/shared/`・`frontend/scripts/`・`scripts/`の既存`.test.mjs`を選ぶ。
- `kind: suite, name: postgres`は`pnpm test:postgres`、`name: browser`は`pnpm test:e2e`、`name: backend-startup`は通常設定のbackend起動確認、`name: source-data`はPMDA構造化データを使う表示確認を選ぶ。source-data suiteは明示選択時だけ実行し、入力がなければ失敗する。通常unitのfixture成功に置き換えない。backend起動確認は`uv run --project backend --locked python -m backend.infrastructure.cli.configured_e2e_gate`を実行し、configured PostgreSQL readinessと実アプリのOS healthを検証する。起動失敗時はtraceback全体や秘密値を出さず、redactしたERROR行と例外要約を品質出力へ返す。DBのmigration・初期登録・更新は行わず、health専用port 3212が使用中なら失敗する。試験所有のprobe processだけを停止する。DB・原本・port等は既存の検証規約に従い、外部LLMの実通信は含まない。
- 空の対応・未知のキー/種類・任意コマンド・存在しないファイル・ディレクトリ外への参照は拒否する。

```sh
pnpm quality:changed --spec docs/development/quality-task.example.json --list
pnpm quality:changed --spec docs/development/quality-task.example.json --phase quick
pnpm quality:changed --spec docs/development/quality-task.example.json --report tmp/quality/results.json
```

実際の作業用はGit管理外の`tmp/quality/task.json`に置くと、手動（`agent:check`等）とStopが同じ仕様を読む。`pnpm agent:check`とStop Hookはコードscopeでこの仕様を必須にする。quickからfullの完了検査とHookの完了判定が終わるまでspecを保持し、その後に削除する。例は開発ツール用なので、製品機能の作業ではその受入条件とテストに書き換える。spec必須を付けない`quality`・`quality:changed`は通常の回帰検査用で、受入specの完了証明ではない。`--scope`より仕様で必要な側を優先して追加し、通常の回帰検査は削らない。同じテストを複数要件が参照しても受入検査は1回にまとめ、要件ID・選択理由を計画とレポートへ残す。

quickは指定unit受入検査と既存の軽量検査、fullは全指定受入検査と通常の回帰検査を行う。integrationはquickで実行しないため、quick成功は作業全体の完了根拠にならない。実行時間上限は既存のrunner各コマンド300秒・Stop全体540秒のまま。大きなintegrationが上限を超えた場合は未解決として報告し、独立実行の結果と区別する。

受入検査ではNode・pytest・Playwrightの最終サマリーから1件以上の成功とskip/xfail/xpass/todoなしを確認する。backend-startupは終了コードに加え、readiness成功とOS healthの`status: ok`が出力されたことを確認する。未実施や未知の出力形式は`incomplete`でゲートを失敗させる。マーカーで対象外とした`deselected`は対象テストの成功件数に加えない。テストの内容が仕様を網羅していること自体は、この集計では証明しない。

実行計画の`testRunner`に従って集計する。Node・pytestは当該実行の最終サマリー、Playwrightはmock・realを含む必要な層のサマリーをまとめて読み、別行や前の層にあるskipも保持する。補助Node実行の成功件数をブラウザ成功件数に加えない。

## 修正フィードバックと停滞検出

失敗時はテストID・型/ lint診断を抽出し、`feedback`に診断、修正手順、検証規約へのリンク、対応要件IDを記録する。例えばF401なら未使用importの削除、型不整合なら公開署名とNoneの絞り込みを提案する。これは診断に応じた修正候補であり、自動patchや正しさの保証ではない。stdout/stderrはコマンド完了時に出力する。Stopはログ参照とこのフィードバックをエージェントへ返す。

同一作業（hookのturn ID、なければsession ID）の連続する失敗集合を診断IDで比較する。行番号・所要時間が変わっても同じ診断なら数える。ファイル内容の変更だけではリセットしない。失敗集合が変われば連続回数をリセットし、成功または作業仕様の変更でもリセットする。同じ集合が3回なら`stagnated`、診断を特定できない場合も含め失敗実行が6回なら`attempt_limit`とし、Stopから追加修正を要求せず未解決と報告するよう通知する。未知のログを同じ原因と断定せず、診断が抽出できない場合は3回判定を使わない。

これはhookの自動継続要求を止める制御であり、Codex本体のprocessを強制終了するものではない。同一入力の再通知は検査を再実行せず、修正やユーザーの介入後に入力が変われば再検証できる。停滞時も失敗の終了コード・ログを保持し、成功へ変換しない。

[Sandboxと承認の記事](https://azukiazusa.dev/blog/codex-sandbox-agent-authorization/)および[公式Rules](https://learn.chatgpt.com/docs/agent-configuration/rules)に従い、品質結果と実行権限は分ける。仕様JSONが選べるのは登録済み検査だけで、承認ルール・サンドボックス・network設定は変更しない。権限/接続のエラーには通常の承認経路で切り分ける候補を返し、`allow`の追加や保護領域の変更を自己修復に使わない。記事中の過去の設定名・OS実装を、この環境の設定としてコピーしない。

`scripts/checks/quality.test.mjs`は隔離Gitリポジトリでrename両側・未追跡・共有設定の検出を確認し、Git管理下のfrontend・scriptsの全Nodeテストがfull計画に含まれることも検査する。新しい配置を追加してこの検査が失敗した場合は、探索範囲を更新する。CI定義の回帰はbackend・frontend・scripts・PostgreSQL入口の存在を検査するもので、GitHub上の実行成功を保証しない。CIはfrontendについても`quality:frontend`全体およびNext.js本番ビルドを実行する。
frontendのNodeテストは[scripts/checks/test-runtime-requirements.json](checks/test-runtime-requirements.json)で追加runtimeを宣言する。Node/Python連携テストは通常unitから分け、レポートへ両runtimeを記録する。新規`.test.mjs`はruntime有無にかかわらずfull計画へ含まれる。`scripts/checks/source-data-guard.mjs --check`はfrontendとscriptsのNodeテストからGit除外PMDA原本・構造化データへの直接パス参照と、`join`/`resolve`で組み立ててファイル読取へ渡すパスを検出する。計算済みパスの伝播や動的import等を網羅的に証明しないため、clean checkout検証を併用する。

`node scripts/checks/verify-clean-checkout.mjs --ref <commit>`は指定commitのdetached worktreeをOS一時領域に作成し、lock済みNode/Python依存の導入と`pnpm quality`を実行する。通常時はworktree内の`.uv-cache`を使う。`--offline`は設定済みの`UV_CACHE_DIR`、未指定時は`uv cache dir`が示す既定cacheを同期と品質検査の両方で再利用し、既存cacheだけから依存を導入する。報告は`tmp/quality/clean-checkout-*.json`へ保存し、試験所有worktreeだけを削除する。未commit差分や未追跡ファイルは対象commitへコピーしない。この入口の成功は指定commitだけの結果であり、現在の作業ツリーやGitHub Actionsの成功へ置き換えない。

`quality:scripts`ではPyYAMLでCI workflowのjob構造・frontend runtime準備・依存同期の順序を検査する。これは定義の検査であり、GitHub Actions上の実行成功は別に確認する。

## Codex hooks

[.codex/hooks.json](../.codex/hooks.json)が登録先。

ここに記載するPostToolUse/Stopイベント形式、receipt、停滞回数はCodex adapter固有。共通の品質計画・`--spec`・JSONレポートは`pnpm agent:check`で別のエージェントからも直接利用できる。編集後と完了前の自動実行には、各製品側でこのコマンドを呼ぶHookが必要。

- `PostToolUse`: ファイル編集ツールの入力を解析し、編集されたPython（Ruff）およびFrontend（Biome）の自動整形と編集ループ検出のみを行う。型・構造・受入検査や`--require-spec`は編集ごとに実行せず、手動の`pnpm agent:check`および終了時の`Stop`差分検査へ集約する。
- `PostToolUse`は対象ファイルの編集回数もターン単位で数える。`apply_patch`・`Edit`・`Write`イベント内の同じパスは1回として扱い、同じリポジトリ内ファイルへの5回目の編集で、受入条件と方針を見直す一度限りの非ブロッキング警告を返す。5回は使用状況で調整する初期ヒューリスティック。
- 編集回数の状態は無視対象の`.agents/work/.hooks/`に、ハッシュ化したターン識別子とリポジトリ相対パス・回数・警告済みマーカーだけを保存する。ファイル本文やプロンプトは保存しない。`Stop`が完了をブロックした場合は状態を維持し、ブロックしない場合は削除する。この警告はシェル経由の編集を数えず、シェル経由の差分は引き続き`Stop`検査が扱う。
- `Stop`: `--require-spec`付きでstaged・unstaged・削除・未追跡を含む変更範囲のfull検査を実行する。文書のみの変更ではcode scopeがなくspecを要求しない。
- 同一ターン・同一内容の成功結果は再利用する。検査中に内容が変わった場合は成功を認定しない。
- 再利用の識別子にはHEAD、差分ファイル、Git管理下のJSON/TOML/YAML/INI/lock設定、`scripts/checks`・`scripts/hooks`、Python/Node版指定、作業用`tmp/quality/task.json`も含める。検査計画や作業仕様の変更でも再検証する。依存環境そのものや外部サービスの状態は識別子の対象外。壊れた証跡は診断を出して再検証する。
- 失敗時は修正を要求する。同じ内容で既に継続した場合は再度継続させず、失敗の報告を促す。環境不足を成功と扱わない。
- 結果とログは`.agents/work/.hooks/`へ保存し、Git管理しない。
- Stopの証跡JSONは入力の識別子・終了コードと、共通ログおよび検査別の`.report.json`への参照を保持する。従来どおり検証中の入力変更を検出した場合は、個別コマンドが正常終了していても証跡を失敗にする。

エディタのMypyも`.vscode/settings.json`で選択中のPython環境の`python -m mypy`、リポジトリルート、`backend/pyproject.toml`へ統一する。既定の拡張同梱Mypyへ暗黙に切り替えない。`scripts/hooks/test_quality_gate.py`で実MypyのOptional引数エラー検出と、hookの失敗通知・Stopブロックを別々に検証する。登録済みhookがCodex上で自動発火したかは、この単体検証とは区別する。

hooks定義の変更後はCodex側で定義を確認・信頼する操作が必要。登録ファイルの存在と実際の自動発火は別々に確認する。[公式仕様](https://learn.chatgpt.com/docs/hooks)

## Antigravity hooks

[.agents/hooks.json](../.agents/hooks.json)が登録先。Codexの`.codex/hooks.json`と同様に`proactive-defense`・`quality-gate`・`privacy-gate`を分離して定義し、イベントアダプター [`scripts/hooks/antigravity_adapter.py`](hooks/antigravity_adapter.py) 経由で呼び出す。

登録コマンドはカレントディレクトリがワークスペースルート・`.agents/`のいずれであってもリポジトリルートを解決し、`backend`と`scripts/hooks/antigravity_adapter.py`を参照する。編集後の品質ゲート通知はPostToolUseの戻り値には含めず、次のPreInvocationで一時メッセージとして渡す。

- `quality-gate`:
  - `PostToolUse` (`matcher: "edit_file|write_file|replace_file_content|write_to_file|multi_replace_file_content"`, timeout 600): ファイル編集後にPython（Ruff）/ Frontend（Biome）の自動整形および編集ループ検出を行う。
  - `PreInvocation` (timeout 30): 直前のPostToolUseで記録した整形失敗・編集ループ警告を`injectSteps`の一時メッセージとしてエージェントへ渡す。PostToolUseの応答は仕様に従い空の`{}`を返す。
  - `Stop` (timeout 600): 差分・未追跡ファイルに対する受入・回帰検査（`--require-spec`付き）を実行し、失敗時は `{"decision": "continue", "reason": "..."}` を返して完了を差し戻す。
- `privacy-gate`:
  - `PostToolUse` (`matcher: "edit_file|write_file|replace_file_content|write_to_file|multi_replace_file_content|run_command"`, timeout 60): 編集に加えシェルコマンド実行後にも個人パス・禁止語の漏洩を即座に検査する。
  - `Stop` (timeout 60): 終了直前に個人パス・禁止語の漏洩を検査し、検出時は完了を差し戻す。

### プライバシー検査

実行用は[`hooks/privacy_gate.py`](hooks/privacy_gate.py)、回帰テストは[`hooks/test_privacy_gate.py`](hooks/test_privacy_gate.py)に集約する。

`privacy_gate.py`は編集・shell実行後（PostToolUse）と終了時（Stop）に、HEADとの差分およびGit管理対象になり得る未追跡テキストを検査する。削除・Git除外ファイル・バイナリ・symlinkは対象外。UTF-8とBOM付きUTF-16を扱い、検出結果は本文を含めずファイルと行番号のみ返す。

現行Git hookと同じくCドライブのUsers配下の個人パスを検出し、APIの`/users/me`、他ドライブ、Unixパスは対象外。ローカルの`~/.config/git/hooks/privacy-config.json`があれば`allowed_user_segments`と`blocked_literals`を利用する。設定がなければホームパス検査のみ行う。禁止語を共有ファイルへ転記しない。

Stopで検出すると一度修正を促し、継続後も残る場合は未解決として通知する。公開済み・送信予定のコミット履歴、画像、アーカイブ、秘密情報全般の検査は行わない。送信する全コミットの検査は既存Git pre-push hookが担当する。手動確認は`echo '{"hook_event_name":"Stop"}' | python scripts/hooks/privacy_gate.py`。実際の自動発火にはCodex側でHooks定義の確認・信頼が必要。
