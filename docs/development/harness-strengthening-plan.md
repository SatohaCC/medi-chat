# Codexハーネス強化案

2026-11-03。`Codexハーネス実装調査.md`と現行ソースを照合した計画。実装・承認済み規約ではない。

## 承認後の実装と検証

同日の実装依頼を受け、優先順位1・2と、3の変更検出・テスト探索・CI入口の回帰検査を実装した。以下の現状・計画本文は調査時点の記録。

- 成功証跡はHEAD、差分内容、管理対象の検査設定・runner定義で無効化する。依存環境・外部サービス状態は識別対象外。
- `--report`で検査別の状態・終了コード・所要時間・コマンドをJSONへ保存する。Stop証跡はログとレポートを参照し、hook全体のタイムアウト・起動不能・検証中の入力変更も状態として記録する。
- 隔離Git fixture、失敗・起動不能・タイムアウトの負例、既存Nodeテストの計画包含、CIの既存入口を回帰検査する。CIの検査範囲自体は変更していない。
- `pnpm quality:scripts --report tmp/quality/harness-scripts-report.json`: 終了コード0。Nodeは22成功・既存Windows skip 2、hook/privacyは18成功。lint・format・Pyright・mypy・生成物照合も成功。レポート実出力を確認。
- `pnpm quality:backend`: 終了コード0。lint・構造検査・型検査成功、DB不要pytestは978成功・346 deselected。実DB・非公開原本を対象外としており、その検証成功は主張しない。最終hook差分の型・format・回帰は上記scriptsゲートで確認。
- `git diff --check`: 終了コード0。実DB・ブラウザ・外部API・GitHub CIの実行・Codex上のhook自動発火は今回未検証。
- 初回の通常権限でのpnpm実行はCorepack取得時のネットワークエラー。権限付き再実行で上記共通ゲートを完了した。失敗記録の目次は当時すでに存在せず、現行規則は追跡対象の設計・検証文書を正本とする。

## 現状

### 追加依頼による第2段階の実装（2026-11-03）

指定された[Sandboxと承認の記事](https://azukiazusa.dev/blog/codex-sandbox-agent-authorization/)と公式Rules/Security/Hooksを読み、品質判断から権限拡張を分離した。仕様JSONは登録済みテストのみ選択し、承認設定・ネットワーク設定・保護領域を変更しない。

- 受入条件とテストの対応を`--spec`または作業用`tmp/quality/task.json`で読み込む。対応理由を計画・レポートへ保持する。通常の回帰検査は維持。受入検査の成功0件・skip/xfail/todo・未知のサマリーは`incomplete`で失敗にする。
- 失敗診断ごとの修正候補・参照規約を返す。診断IDの集合でソース内容と独立に同一失敗を追跡し、3回の反復は`stagnated`、6回の失敗試行は`attempt_limit`としてhookの自動修正要求を止める。未知の診断は同一原因と断定しない。
- `pnpm quality:scripts --spec docs/development/quality-task.example.json --report tmp/quality/harness-phase2-report.json`: 終了コード0。指定Node受入6件、Python受入1件成功。通常Nodeは28成功・既存Windows skip 2、hook/privacyは21成功。lint・format・型・生成物確認も成功。JSONで要件別の成功件数と未選択層を確認した。
- `pnpm quality:backend`: 終了コード0。lint・構造・format・型検査成功、DB不要pytestは978成功・346 deselected。最終診断抽出のJS差分は上記scriptsゲートで確認した。
- 実Nodeの失敗を使った負例、仕様の不正入力、成功0件/skip、変更後も続く失敗の停止、進展・成功による回数リセットを確認した。初回の実Node負例は親Nodeテストの実行コンテキスト継承で子が走らず失敗し、fixtureの環境分離で修正した。初回共通ゲートのimport順違反も修正後に再実行した。
- 実DB・ブラウザ・外部LLM・GitHub上のCI・Codex上の自動発火は今回未検証。使用方法と限界は`scripts/README.md`を正本とする。作業用の有効なdefault仕様は配置せず、再利用可能な例を追加した。

- `scripts/checks/quality.mjs`は手動・CI・hooksの共通入口。quick/full、変更範囲選択、各コマンドのタイムアウト、失敗時の非0終了を実装済み。
- `scripts/hooks/quality_gate.py`は編集後のquick、Stop時のfull、内容のfingerprint、成功結果の再利用、検証中の変更検知を実装済み。
- Stopの同内容の失敗は再継続時に通知して停止できる。これは成功認定ではない。
- DB・ブラウザ・外部APIは共通ゲートと別層。通常ゲートの成功で実接続を保証しない。
- `.codex/hooks.json`の登録は確認できるが、今回のチャットでの自動発火・信頼状態は未確認。
- 当時の作業案内が参照していた失敗記録の目次は存在しなかった。過去のGraphify記録の存在や承認状態を現行規約の根拠にしない。

### 追加依頼による第3段階: 同一ファイルの反復編集警告（2026-11-03）

[LangChainのharness engineering記事](https://www.langchain.com/blog/improving-deep-agents-with-harness-engineering)を参考に、同一ファイルへの反復編集に対する早期の再考促進を追加した。

- 既存の`PostToolUse` adapterが認識する`apply_patch`・`Edit`・`Write`イベントについて、ターン内のファイル編集回数を保持する。イベント内の重複パスは1回にまとめる。
- 同一のリポジトリ内ファイルが5回編集された時点で、一度だけ受入条件と方針の見直しを促す。助言のみで、品質検査や作業をブロックしない。
- 状態は`.agents/work/.hooks/`の無視対象JSONに限定し、ハッシュ化したターン識別子、相対パス、回数、警告済みマーカーのみを保存する。停止がブロックされた間は保持し、ブロックなしで停止できる場合に削除する。
- 5回はローカルの編集トレースから計測した値ではなく、初期ヒューリスティック。記事のTerminal Bench成績やモデル別推論配分はこのプロジェクトの設定根拠にしていない。
- 回帰テストは`test_post_edit_warns_once_after_five_edits`、`test_post_edit_counts_unique_paths_per_turn_and_keeps_state_private`、`test_edit_counts_survive_blocked_stop_and_clear_after_allowed_stop`。
- `pnpm agent:check --phase quick`と`pnpm agent:check --report tmp/quality/result.json`は終了コード0。quick・fullとも指定した受入テスト3件が成功。fullではDB不要backendテスト978件成功・346件deselected、Hook回帰24件成功、format・型・構造・生成物検査が成功した。通常の開発ツールNode試験は29件成功・Windows外部シグナル2件skip。
- fullレポートの`excludedLayers`は`postgres`・`browser`・`external_api`。Codexアプリ上のHook自動発火・信頼状態は未検証。
- シェル経由の編集はこの回数警告の対象外で、終了時の差分検査が扱う。

### 追加依頼による第4段階: ハーネス構成要素との照合（2026-11-03）

[LangChainのハーネス解説](https://www.langchain.com/blog/the-anatomy-of-an-agent-harness)は、モデルの外側にある指示・ツール・実行環境・状態・フィードバック・オーケストレーションをハーネスとしてまとめ、望むエージェント動作から必要な部品を決める考え方を示している。medi-chatの開発用ハーネスを次のように照合した。

| 望む動作 | 既存の仕組み | 所有範囲・限界 |
|---|---|---|
| 作業と判断材料を保持する | リポジトリのfilesystem・Git、`AGENTS.md`と対象別資料、`tmp/quality/task.json`、`.agents/work/.hooks/`の検査ログ・証跡 | `task.json`は作業用で、完了時に削除する。Git差分・作業文書を長期の普遍的な記憶とみなさない。 |
| 操作を実行し、安全な結果を得る | Codexのファイル・shell等のツール、`scripts/checks/quality.mjs`の共通runner | filesystem・shell・networkの権限とsandboxはCodex側が所有する。品質判定のためにrepoから権限を広げない。 |
| 実行結果から修正し、完了を判定する | `PostToolUse` quick、`Stop` full、受入条件とテストの対応付け、構造化レポート | fullは別の実行段階だが、評価はリポジトリ内の検査に依存し、外部評価器と同等に独立ではない。DB・browser・外部APIも別層。 |
| 必要な知識を選び、長い作業を続ける | `AGENTS.md`の条件付き資料案内、skillsの段階的参照、Gitと作業記録 | 会話のcompaction・大きなtool出力の退避はCodex側の責務。repo hookは失敗の停滞を止めるが、新しいcontextで自律的に再起動するRalph loopは管理しない。 |
| 最新情報と並列化を使う | Web/MCP、subagent、役割定義は実行環境が提供 | Web/MCPはrepo外の機能。プロジェクトのfeature-pipelineは明示開始時だけ使う。タスクからsubagentや常駐orchestratorを自動起動しない。 |

この照合では、既存の開発作業で使う部品は揃っており、articleの一覧を機能追加チェックリストとして扱う必要はないと判断した。runtimeや権限の変更は行わない。将来追加する場合は、具体的なagent behavior gap、受入条件、所有する実行環境を先に定めてから設計する。

- 2026-11-03、ユーザーはこの構成要素の照合結果を承認した。

## 優先順位と受入条件

### 1. 検証証跡を現在の検証入力に結び付ける

対象: `scripts/hooks/quality_gate.py`とその回帰テスト。

現行signatureはHEADとの差分ファイル名と内容を対象にする。HEAD、変更されていない検査設定、実行計画は含まれない。検証が依存する入力を定義してから、成功結果の再利用条件へ追加する。全ファイルを毎回hashする設計は先に採用しない。

受入条件:

- 同一入力の成功は再利用できる。
- HEAD・検査設定・実行計画が変化した場合、古い成功を再利用しない。
- 検査中に対象入力が変われば成功を認定しない。
- 壊れた証跡は診断を返し、成功として再利用しない。

### 2. 検査結果を構造化する

対象: `scripts/checks/quality.mjs`、`scripts/checks/quality.test.mjs`、hookとそのテスト、`scripts/README.md`。

既存の人向け出力を保持し、検査単位の状態、コマンド、所要時間、終了コード、ログ参照、検証入力の識別子を機械可読に記録する。状態は少なくとも成功・コマンド失敗・起動不能・タイムアウト・未実施を区別する。テスト内部のskip/xfail件数は、出力解析を実装しない限り把握したと扱わない。

受入条件:

- 非0終了・起動不能・タイムアウトをそれぞれ隔離した負例で検出できる。
- 必須検査の未実施を全体成功として扱わない。
- 共通ゲートの記録からDB・ブラウザ・外部APIを検証済みと読めない。
- 出力先に秘密値・全環境変数・ユーザープロンプトを保存しない。

### 3. 変更範囲選択とCIの対象を契約として検査する

対象: quality runnerと回帰テスト、必要時にCI。

`scopesFor`のパス規則と`nodeTests`の探索ルートは固定列挙。新しいディレクトリの検査漏れと、ルート`quality`のfrontend検査がCIでどこまで実行されるかを明示する。文書だけの変更は従来どおりコード検査を起動しない。

受入条件:

- staged・unstaged・削除・rename・未追跡・共有設定の変更を隔離したGit fixtureで確認する。
- 新規テスト配置が探索対象に入ること、対象外の場合の扱いを確認する。
- ローカル実行計画とCIの実行範囲の差を説明できる。

### 4. 停滞制御は既存Stop処理を拡張する

現行の同内容失敗の再停止抑制を保持する。内容を少しずつ変えた同一失敗の反復について、検査IDと正規化した失敗情報で検出する案を評価する。異なる失敗や修正による進展を停滞としない。上限到達は未解決として報告し、品質ゲートを緩和しない。

App Serverや常駐の自律オーケストレーターを追加する必要性は現時点で立証されていない。ターン数・トークン予算の全体管理はrepo hookだけで保証できるものとして設計しない。

## 調査文書を適用する際の留保

- Rulesの`allow`はサンドボックス外実行を確認なしで許可する設定。検証コマンドだからという理由で包括的に追加しない。[公式Rules](https://learn.chatgpt.com/docs/agent-configuration/rules)
- Windowsの実装やnetworkの可否は実行環境・設定に依存する。文書の一律の説明をこの環境の事実として扱わない。[公式Security](https://learn.chatgpt.com/docs/agent-approvals-security)
- モデル別成功率・費用、guardianの閾値・待ち時間、固定の5〜8ターンは今回一次資料で検証していない。採用する設計定数や効果の保証に使わない。
- [Martin Fowlerの記事](https://martinfowler.com/articles/are-harnesses-worth-the-cost.html)は、1つの詳細なJavaサービス課題を各モデル10回実行した小規模実験で、GPT-6 Solはハーネス有無とも10/10合格、GPT-6 Lunaはハーネスなし3/10・あり10/10だったと報告する。Solのハーネスありはなしより約10.5倍のtoken、約3倍の時間、約7倍の推定費用を使った一方、Lunaでは継続フィードバックが合格率を高め、ハーネスありLunaはハーネスなしSolより平均費用が約33%低かった。これはモデル能力だけでなく課題・仕様の詳細さにも左右され、既存コード変更やこのプロジェクトへそのまま一般化できない。
- この記事の実務上の示唆は、モデルや作業で開発中センサーの頻度を調整しつつ、全モデルで独立した最終受入検査を保つこと。プロジェクトでは`PostToolUse`のquickと`Stop`のfullがこの二段階に当たる。ただしfullは独立の外部評価器ではなく、同じリポジトリの検査と受入テストを実行するため、その独立性には限界がある。
- 変更前の参考値として、2026-11-03の`pnpm quality:changed --phase quick --report tmp/quality/harness-cost-quick.json`は全4検査が成功し、Python lint 112ms、Backend Mypy 25,499ms、runner構文74ms、Tooling lint 141msだった。同じquick計画内の2つのlintは`scripts/checks`・`scripts/hooks`を重複して検査しており、この1回では合計253ms。単発の時間は環境・cache・入力差を含み、編集ごとのHook実行回数や早期検出した不具合数、総作業費用は測っていない。
- 現時点では編集後Mypyを含むquickの頻度を下げない。過去に編集時の型診断とquickに型検査がない問題があり、その後Mypyを追加している。今回の1回の時間測定だけでは、その早期検出価値と繰り返し費用の比較ができない。まず同一の受入条件で代表的な作業・モデル・feedback cadenceを比較し、PostToolUse回数、総所要時間、検査が修正前に捕捉した不具合、最終ゲート結果を記録する。頻度変更は最終ゲートの範囲と合格条件を維持したまま、失敗率を悪化させず総費用を下げる根拠が得られた場合に限る。
- 2026-11-03、ユーザー承認を受けてこの判断を採用した。運用上の比較条件は[validation](validation.md#共通の実行入口)に記載した。

## 着手順と検証

第1段階は優先順位1・2を対象として、テスト仕様を確認してから実装する。第3・4段階は別変更で評価する。feature-pipelineは明示的な開始依頼がある場合のみ使用する。

今回実行したのは`node --test scripts/checks/quality.test.mjs`のみ。終了コード0、7件成功、skipなし。runnerの既存回帰であり、hook自動発火・Python hook・実品質全体・DB・ブラウザ・CIは今回検証していない。

実装時は対象の負例・回帰、`pnpm quality:scripts`を実行し、hook変更がbackendスコープも選択するため、その計画に含まれる検査も確認する。hooksを変更する場合は定義の検査とCodex上の実発火を別に記録する。
