# 開発ツールと品質検査

テスト本体とlint・型検査設定は`backend/`・`frontend/`が所有する。共有の実行入口は`checks/quality.mjs`。手動・CI・Codex hooksはこの入口から同じパッケージコマンドを呼ぶ。

| 場所 | 責務 |
| --- | --- |
| `checks/` | 品質検査の実行とApplication・Domainの構造検査 |
| `hooks/` | Codexイベントの解析、編集ファイル判定、整形、検査結果の返却と重複実行防止 |
| `postgres/` | PostgreSQLの初期化 |
| 直下のスクリプト | 開発サーバー起動、環境解決、生成データの出力 |

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
```

`full`は対象側のlint・format確認・型検査・単体テストを実行し、backendでは構造検査も含む。`scripts`ではツールの回帰と生成物の整合性も検査する。`quick`はlint・実行入口の構文確認に加え、backendではプロジェクトのMypyを`--no-incremental -p backend`で実行する。失敗・起動不能・タイムアウトは非0で終了し、他の検査も続けて結果を表示する。一時ファイルとuvキャッシュはプロジェクト内のGit管理外領域を使う。

実PostgreSQL・ブラウザ・外部APIは変更パスだけから自動選択しない。実PostgreSQL・ブラウザは下の仕様JSONで明示選択できる。必要な前提は[検証手順](../docs/development/validation.md)を参照する。CIは共通のbackend・scripts検査に加え、実PostgreSQL契約を実行する。

`--report <path>`は実行前に全検査を`not_run`として保存し、各検査後に状態・終了コード・所要時間・コマンドを更新する。状態は`passed`・`failed`・`start_error`・`timeout`・`incomplete`・`not_run`。空の実行計画は終了コード0でもレポートでは`not_run`とする。通常の回帰検査の`passed`はコマンドの正常終了を示す。仕様から追加した受入検査は後述の成功件数とskipも確認する。未選択の実DB・ブラウザ・外部APIは`excludedLayers`に記録する。選択しただけの層を検証成功と扱わず、各taskの状態を確認する。

## 仕様に基づくテスト選択

作業の受入条件を[仕様JSONの例](../docs/development/quality-task.example.json)の形式でテストへ対応付ける。`version: 1`、作業を示す`task`、要件ごとの一意な`id`・`acceptance`・空でない`checks`が必須。自然言語からテストの意味を推測する仕組みではなく、対応付けの妥当性は仕様レビューで確認する。

- `kind: python`は`backend/tests/`または`scripts/hooks/`の既存テストを選ぶ。任意の`test`にpytestの関数・クラス・`TestClass::test_method`を指定できる。実DB・非公開原本のマーカーは除外されるため、それらが必要なら通常のunit指定で代替しない。
- `kind: node`は`frontend/features/`・`frontend/shared/`・`frontend/scripts/`・`scripts/`の既存`.test.mjs`を選ぶ。
- `kind: suite, name: postgres`は`pnpm test:postgres`、`name: browser`は`pnpm test:e2e`を選ぶ。DB・原本・port等は既存の検証規約に従う。外部LLMの実通信は含まない。
- 空の対応・未知のキー/種類・任意コマンド・存在しないファイル・ディレクトリ外への参照は拒否する。

```sh
pnpm quality:changed --spec docs/development/quality-task.example.json --list
pnpm quality:changed --spec docs/development/quality-task.example.json --phase quick
pnpm quality:changed --spec docs/development/quality-task.example.json --report tmp/quality/results.json
```

実際の作業用はGit管理外の`tmp/quality/task.json`に置くと、手動・PostToolUse・Stopが自動で同じ仕様を読む。作業が終わったらこの作業用ファイルを削除する。例は開発ツール用なので、製品機能の作業ではその受入条件とテストに書き換える。明示した`--spec`がない場合、作業用ファイルもなければ従来のパス選択を使う。`--scope`より仕様で必要な側を優先して追加し、通常の回帰検査は削らない。同じテストを複数要件が参照しても受入検査は1回にまとめ、要件ID・選択理由を計画とレポートへ残す。

quickは指定unit受入検査と既存の軽量検査、fullは全指定受入検査と通常の回帰検査を行う。integrationはquickで実行しないため、quick成功は作業全体の完了根拠にならない。実行時間上限は既存のrunner各コマンド300秒・Stop全体540秒のまま。大きなintegrationが上限を超えた場合は未解決として報告し、独立実行の結果と区別する。

受入検査ではNode・pytest・Playwrightの最終サマリーから1件以上の成功とskip/xfail/xpass/todoなしを確認する。未実施や未知の出力形式は`incomplete`でゲートを失敗させる。マーカーで対象外とした`deselected`は対象テストの成功件数に加えない。テストの内容が仕様を網羅していること自体は、この集計では証明しない。

## 修正フィードバックと停滞検出

失敗時はテストID・型/ lint診断を抽出し、`feedback`に診断、修正手順、検証規約へのリンク、対応要件IDを記録する。例えばF401なら未使用importの削除、型不整合なら公開署名とNoneの絞り込みを提案する。これは診断に応じた修正候補であり、自動patchや正しさの保証ではない。stdout/stderrはコマンド完了時に出力する。Stopはログ参照とこのフィードバックをエージェントへ返す。

同一作業（hookのturn ID、なければsession ID）の連続する失敗集合を診断IDで比較する。行番号・所要時間が変わっても同じ診断なら数える。ファイル内容の変更だけではリセットしない。失敗集合が変われば連続回数をリセットし、成功または作業仕様の変更でもリセットする。同じ集合が3回なら`stagnated`、診断を特定できない場合も含め失敗実行が6回なら`attempt_limit`とし、Stopから追加修正を要求せず未解決と報告するよう通知する。未知のログを同じ原因と断定せず、診断が抽出できない場合は3回判定を使わない。

これはhookの自動継続要求を止める制御であり、Codex本体のprocessを強制終了するものではない。同一入力の再通知は検査を再実行せず、修正やユーザーの介入後に入力が変われば再検証できる。停滞時も失敗の終了コード・ログを保持し、成功へ変換しない。

[Sandboxと承認の記事](https://azukiazusa.dev/blog/codex-sandbox-agent-authorization/)および[公式Rules](https://learn.chatgpt.com/docs/agent-configuration/rules)に従い、品質結果と実行権限は分ける。仕様JSONが選べるのは登録済み検査だけで、承認ルール・サンドボックス・network設定は変更しない。権限/接続のエラーには通常の承認経路で切り分ける候補を返し、`allow`の追加や保護領域の変更を自己修復に使わない。記事中の過去の設定名・OS実装を、この環境の設定としてコピーしない。

`scripts/checks/quality.test.mjs`は隔離Gitリポジトリでrename両側・未追跡・共有設定の検出を確認し、Git管理下のfrontend・scriptsの全Nodeテストがfull計画に含まれることも検査する。新しい配置を追加してこの検査が失敗した場合は、探索範囲を更新する。CI定義の回帰はbackend・scripts・PostgreSQL入口の存在を検査するもので、GitHub上の実行成功を保証しない。現在のCIはfrontendについて認証ヘルパー単体を実行し、`quality:frontend`全体は実行しない。

## Codex hooks

[.codex/hooks.json](../.codex/hooks.json)が登録先。

- `PostToolUse`: ファイル編集ツールの入力を解析し、編集されたPythonだけをRuff整形した後、対象側のquick検査を実行する。シェル経由の編集は終了時の差分検査で拾う。
- `Stop`: staged・unstaged・削除・未追跡を含む変更範囲のfull検査を実行する。文書のみの変更ではコード検査を起動しない。
- 同一ターン・同一内容の成功結果は再利用する。検査中に内容が変わった場合は成功を認定しない。
- 再利用の識別子にはHEAD、差分ファイル、Git管理下のJSON/TOML/YAML/INI/lock設定、`scripts/checks`・`scripts/hooks`、Python/Node版指定、作業用`tmp/quality/task.json`も含める。検査計画や作業仕様の変更でも再検証する。依存環境そのものや外部サービスの状態は識別子の対象外。壊れた証跡は診断を出して再検証する。
- 失敗時は修正を要求する。同じ内容で既に継続した場合は再度継続させず、失敗の報告を促す。環境不足を成功と扱わない。
- 結果とログは`.agents/work/.hooks/`へ保存し、Git管理しない。
- Stopの証跡JSONは入力の識別子・終了コードと、共通ログおよび検査別の`.report.json`への参照を保持する。従来どおり検証中の入力変更を検出した場合は、個別コマンドが正常終了していても証跡を失敗にする。

エディタのMypyも`.vscode/settings.json`で選択中のPython環境の`python -m mypy`、リポジトリルート、`backend/pyproject.toml`へ統一する。既定の拡張同梱Mypyへ暗黙に切り替えない。`scripts/hooks/test_quality_gate.py`で実MypyのOptional引数エラー検出と、hookの失敗通知・Stopブロックを別々に検証する。登録済みhookがCodex上で自動発火したかは、この単体検証とは区別する。

hooks定義の変更後はCodex側で定義を確認・信頼する操作が必要。登録ファイルの存在と実際の自動発火は別々に確認する。[公式仕様](https://learn.chatgpt.com/docs/hooks)

### プライバシー検査

実行用は[`hooks/privacy_gate.py`](hooks/privacy_gate.py)、回帰テストは[`hooks/test_privacy_gate.py`](hooks/test_privacy_gate.py)に集約する。legacyにあった旧グローバルhookのコピーと試験スクリプトはこの構成へ置き換え済み。個人環境を書き換える一回限りの更新スクリプトは廃止した。

`privacy_gate.py`は編集・shell実行後（PostToolUse）と終了時（Stop）に、HEADとの差分およびGit管理対象になり得る未追跡テキストを検査する。削除・Git除外ファイル・バイナリ・symlinkは対象外。UTF-8とBOM付きUTF-16を扱い、検出結果は本文を含めずファイルと行番号のみ返す。

現行Git hookと同じくCドライブのUsers配下の個人パスを検出し、APIの`/users/me`、他ドライブ、Unixパスは対象外。ローカルの`~/.config/git/hooks/privacy-config.json`があれば`allowed_user_segments`と`blocked_literals`を利用する。設定がなければホームパス検査のみ行う。禁止語を共有ファイルへ転記しない。

Stopで検出すると一度修正を促し、継続後も残る場合は未解決として通知する。公開済み・送信予定のコミット履歴、画像、アーカイブ、秘密情報全般の検査は行わない。送信する全コミットの検査は既存Git pre-push hookが担当する。手動確認は`echo '{"hook_event_name":"Stop"}' | python scripts/hooks/privacy_gate.py`。実際の自動発火にはCodex側でHooks定義の確認・信頼が必要。
