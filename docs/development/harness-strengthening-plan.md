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
- 初回の通常権限でのpnpm実行はCorepack取得時のネットワークエラー。権限付き再実行で上記共通ゲートを完了した。失敗記録の目次は引き続き存在しない。

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
- 指示で参照される`.agents/lessons/INDEX.md`は存在しない。過去のGraphifyにある記録の存在や承認状態を現行規約の根拠にしない。

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
- 高性能モデルなら中間検査を省く、という結論は本プロジェクトでは未評価。現行quick/fullを基準とし、削減は実測で判断する。

## 着手順と検証

第1段階は優先順位1・2を対象として、テスト仕様を確認してから実装する。第3・4段階は別変更で評価する。feature-pipelineは明示的な開始依頼がある場合のみ使用する。

今回実行したのは`node --test scripts/checks/quality.test.mjs`のみ。終了コード0、7件成功、skipなし。runnerの既存回帰であり、hook自動発火・Python hook・実品質全体・DB・ブラウザ・CIは今回検証していない。

実装時は対象の負例・回帰、`pnpm quality:scripts`を実行し、hook変更がbackendスコープも選択するため、その計画に含まれる検査も確認する。hooksを変更する場合は定義の検査とCodex上の実発火を別に記録する。
