# ハーネスの再現性と完了判定の強化計画

2026-11-04。評価対象はローカルmainの`5521982`と直近4コミット。ユーザー承認を受けて実装した追加計画で、確認結果と未解決層を末尾に記録する。コミットは作成していない。[従来の計画と実装記録](harness-strengthening-plan.md)に対する追加計画とする。

## 目的と維持する契約

「ローカルで通った検査」を、入力・実行環境・受入条件が明確な再現可能な証跡へ近づける。次の既存契約は維持する。

- 共通入口は`pnpm agent:check`と側別の`quality:*`。quick/fullの検査範囲・型検査頻度を弱めない。
- 受入検査の成功0件・skip/xfail/xpass/todo・未知の出力を成功にしない。通常の回帰検査と受入検査の証跡を区別する。
- PostgreSQL・ブラウザ・外部APIは別層。環境不足も非0終了とし、未実施を成功へ変換しない。
- DB検証は所有資源とread-only契約を維持する。診断のためにmigration・初期登録・既存processの停止を自動実行しない。
- 仕様とテストの意味的な対応はレビューで確認する。ハーネスの正常終了だけで仕様網羅・安全性全般を保証しない。

正本は[scripts/README](../../scripts/README.md)、[validation](validation.md)、[backend設計の変更時の確認](../architecture/backend-design.md#変更時の確認)。実装時はfrontendの案内と対象Next.jsガイドも確認する。

## 現在の根拠と制約

- `SourceEvidenceContent.test.mjs`はローカルの検索生成物があれば使用し、なければ追跡済みfixtureへ切り替える。同一テスト名でも入力が環境依存になる。
- `semantic-compare.test.mjs`はPythonを呼ぶ。CIのfrontendジョブにはPython/uvセットアップが追加済みだが、回帰検査はCIコマンドの文字列の存在確認に留まる。
- `loadSpecification`は作業用specがない場合に通常検査へ進む。受入作業でspecを必須にする規約はCLIでは強制されない。
- DB到達確認は`OSError`全般を捕捉し、出力理由を一律`connection_refused`にする。低レイヤーの`schema_not_ready`契約は復元済み。
- 初回評価時はローカルの失敗記録運用文書が欠けていた。後続確認で、現在の規則は追跡対象の設計・検証文書に統合済みと判断し、運用機構を廃止した。
- 評価時の限定検証はNode 24件、診断pytest 6件、表示/Python連携Node 7件が成功、skipなし。実DB・ブラウザ・全品質・本番buildは未実行。ローカル検索生成物は存在した。GitHub接続不能のため最新CI状態は未確認。

## 実装単位と着手順

各段階を独立したレビュー可能な変更にする。段階ごとに受入条件とテスト仕様を確認してから実装し、次段階へ進む。feature-pipelineは明示的な開始依頼がある場合だけ使う。

| 段階 | 優先度 | 成果物 | 主な変更対象 |
|---|---|---|---|
| 1 | 高 | 入力が固定されたunitと未追跡依存の検出 | 表示テスト・fixture、scripts/checks、validation |
| 2 | 高 | ランタイム要件とCIジョブの整合検査 | quality runner、CI契約テスト、workflow |
| 3 | 高 | クリーン環境で対象commitを検証する入口 | scripts/checks、CI、scripts/README |
| 4 | 高 | specがない受入作業を完了認定しない入口 | quality-spec、quality runner、Hook adapterとテスト |
| 5 | 中 | 契約を維持したDB診断と有効な文書参照 | configured_e2e_gate、診断テスト、作業案内 |

### 1. テスト入力の固定と局所的な依存ガード

通常の`SourceEvidenceContent` unitは追跡済みfixtureだけを読む。実データでの表示確認は別の明示実行に分離し、入力不足時にfixtureへ代替しない。fixtureは作成根拠・再生成方法を説明し、手作業fixtureで原本からの取り込み経路まで検証したとは扱わない。

通常unitから禁止するローカル資源を定義し、まずPMDA原本・生成物への直接参照を検出する。全`.gitignore`対象の一律禁止は行わない。依存パッケージ・一時出力・テストが自ら生成する資源を区別する。単純な文字列検索だけに依存せず、ファイル読取とパス構築の対象を検査し、検出できる構文と限界を文書化する。動的な依存の検出は段階3で補う。

受入条件:

- H1-A: ローカルPMDAデータの有無で通常unitの入力が変わらない。実データへのフォールバックを残さない。
- H1-B: 禁止されたローカルデータを直接読む負例をガードが検出し、追跡済みfixture・一時生成物の正当な使用は拒否しない。
- H1-C: 明示的な実データ検査は入力不足を非0で報告し、通常unit成功で代替しない。

テスト仕様: 隔離したテスト用ディレクトリと小さな負例を使う。利用者の既存データをrename・削除して分岐を試さない。ガード自身の負例fixtureは通常unitの依存違反として誤検出しない配置にする。

### 2. ランタイム要件とCIジョブの整合

Nodeのみの検査とPython連携検査を共通計画内の別taskにする。Python連携は明示登録し、未登録テストの取りこぼしを既存の全Nodeテスト包含検査で防ぐ。新しい外部process呼出しはランタイム宣言を確認するレビュー対象とし、識別できる直接呼出しをガードする。動的import等を含む完全な依存推論は主張しない。

CIは当初、既存frontendジョブのPython/uv環境を保持し、検査だけを分離する。ジョブを増やす判断は計測後に行う。Node単体ジョブへの分割を採用する場合も、Python連携検査を必須CIから外さない。

workflowを構造として読み取り、ジョブごとにcheckout・依存install・Node/Python/uv準備と検査順を検証する。コマンドが別ジョブやコメントにあるだけで合格させない。既存のYAML利用状況を確認し、必要なparser導入は依存変更としてレビューする。

受入条件:

- H2-A: 現在のfrontend全Nodeテストが、Node単体またはPython連携taskに重複なく含まれる。
- H2-B: CIのPython準備削除、別ジョブへの移動、準備前の連携テスト実行を負例として拒否する。
- H2-C: backend・scripts・実PostgreSQL・frontend・本番buildの必須入口を維持する。
- H2-D: 計画とレポートから実行taskと必要ランタイムを識別でき、ランタイム不足は成功にならない。

テスト仕様: workflowの構造を変更した小さな負例、テスト集合の排他性と和集合、実Python連携の代表1件を検証する。CI定義の単体検査とGitHub上の実成功は別に記録する。

### 3. 対象commitのクリーン再現性検証

CIのクリーンcheckoutで、追跡済みの原本/fixtureとlockされた依存だけから通常検査を実行する。新たな重複ジョブを先に追加せず、既存CIジョブが既に満たす範囲を確認して不足を補う。キャッシュは依存の高速化に限定し、ローカル生成データで不足入力を埋めない。

ローカルでも対象commitを明示して一時領域へexportし、同じ検査を実行できる入口を設ける。未コミット差分や未追跡ファイルを暗黙にコピーしない。依存は一時領域でlockに従って用意し、作業ツリーのnode_modulesやvenvへ依存しない。network・ツール不足は環境エラーとして報告する。

受入条件:

- H3-A: 対象commit、検査コマンド、結果、除外層を記録し、別commitや未コミット変更の成功証跡として再利用しない。
- H3-B: ローカルだけにあるファイルを読む負例は、通常作業領域で成功してもexport先で失敗する。
- H3-C: 追跡済みfixtureだけの正例はexport先で成功する。
- H3-D: export・終了時の後始末は試験が所有する一時領域に限定し、既存作業ツリー・DB・原本・既存processを変更しない。

テスト仕様: 小さな隔離Gitリポジトリで所有範囲・対象commit・追跡/未追跡依存を確認し、その後に実リポジトリの指定commitで通常ゲートを実行する。未コミット実装は先に通常の共通ゲートで検証する。commit作成を要する実証は実際のcommitを対象とし、別snapshotをそのcommitの証跡と呼ばない。

### 4. 受入仕様の必須化と完了証跡

共通CLIに`--require-spec`を追加し、コード変更を扱う`agent:check`と対応Hookから利用する。明示specまたは作業用specがない場合は検査開始前に非0とし、何が不足しているかを返す。文書だけの変更や側別の通常CI検査にはspecを強制しない。

specなしで通常ゲートを実行する用途は維持するが、それを要件別の受入完了と表示しない。quickではintegrationを実施しない現在の区別を維持する。受入specは最後の完了検査と必要なStop処理が終わるまで保持し、削除によって未検証扱いへ戻るライフサイクルを避ける。

受入条件:

- H4-A: コード変更の受入入口はspec欠落・不正・空の要件を拒否する。文書のみの変更と通常CIは不要なspecを要求しない。
- H4-B: 要件に対応する検査の成功0件・skip/xfail/xpass/todo・未知出力・起動不能・timeoutを非成功として保持する。
- H4-C: quickで省略されたintegrationを完了済みにしない。通常回帰検査も減らさない。
- H4-D: Hookと手動CLIが同じ必須化規則を使い、spec変更時に古い成功を再利用しない。完了までspecを保持する手順が説明されている。

テスト仕様: spec有無、変更scope、quick/full、手動/Hookを組み合わせた境界ケースを既存テストへ追加する。意味的に無関係なテストの登録まで自動検出できるとは扱わない。Hook定義の登録とアプリ上の自動発火は別検証とする。

### 5. DB診断の精度と規約参照の整備

接続失敗の分類はCLI/Probe層が所有する。TCPの接続拒否・名前解決失敗・timeoutを区別し、未知の`OSError`を接続拒否と断定しない。認証・権限・TLS・schemaの失敗を「DB未起動」に一括変換しない。TCP成功後の接続失敗も下位契約を維持した上位診断として扱う。根拠なく細分化せず、判定不能ならそのまま示す。

Docker起動案内はローカル接続先に適合する場合に提示し、リモート接続先へ一律に推奨しない。ログは既存の秘密値redact方針を維持する。

評価時に見つかった失敗記録機構はローカルGit除外の資料で、運用目次・候補ルール・ひな形が欠けていた。現行の規則は設計・検証文書に統合済みで、新たな候補の承認・整理も必要ないため、機構とその有効な手順参照を廃止する。現在の作業案内と規約文書だけをリンク検査する。

受入条件:

- H5-A: 接続拒否・DNS・timeout・未知エラーの診断を決定的に検証し、環境不足も終了コード1を維持する。
- H5-B: 低レイヤーの`schema_not_ready`契約と既存DB契約テストを維持し、認証・schema不整合を接続拒否と誤表示しない。
- H5-C: 診断へ資格情報・token・接続URLの秘密値を出さず、所有していない資源を変更しない。
- H5-D: 今回扱う作業案内と規約正本のローカルMarkdown参照が実在し、承認状態を誤って引き継がない。

テスト仕様: socket失敗は固定portの空きを仮定せずmonkeypatchで再現する。TCP成功後の失敗と既存DB契約は別に確認する。実DB検証では試験専用PostgreSQLを使用し、通常設定の起動確認とは結果を分ける。リンク検査の対象は今回の規約正本に限定し、過去の履歴全体の整理へ拡大しない。

## 検証と完了判断

実装時はこの受入IDを`tmp/quality/task.json`へ対応付ける。新規テストは実装後に実在する登録可能なパスを指定し、未作成テストを登録済みと呼ばない。完了判定が未解決の間は作業用specとレポートを保持する。

1. 各段階の負例が意図した理由で失敗することを確認し、実装後に正例・既存回帰を実行する。
2. 編集後に`pnpm agent:check --phase quick`、完了前に`pnpm agent:check --report tmp/quality/result.json`を実行する。段階4以降はspec必須の新しい入口契約も確認する。
3. scripts変更では`quality:scripts`、frontendテスト変更では`quality:frontend`、DB診断変更では既存の実PostgreSQL契約を追加で確認する。共通計画で同じ検査が完了済みなら不要に重複実行しない。
4. クリーン環境の結果、GitHub CI、通常設定の起動、実DB、ブラウザ、外部API、Hook実発火はそれぞれ実施/未実施を示す。環境不足・skipを合格に数えない。
5. 証跡には対象版、コマンド、終了コード、件数、skip等、除外層を残す。GitHubへ接続できなければローカル成功とCI未確認を分ける。

効果は「未追跡依存・runtime不足・spec欠落・診断誤分類の負例を検出できること」で評価する。実行時間は同一入力・cache条件を区別して記録し、quick/fullの検査を削る根拠にしない。

## 実行結果と残件

2026-11-04、ユーザー承認後に段階1〜5を実装し、対象テストと共通ハーネスを実行した。

| 段階 | 結果 | 検証証跡・制約 |
|---|---|---|
| 1 入力固定・データガード | 実装済み | SourceEvidence unit 6件、パスガード4件、明示実データsuite 1件が成功。ガードは直接パスと`join`/`resolve`で作られた読取引数・変数を検出する。動的importや任意の別名経由を網羅しない。 |
| 2 runtime・CI契約 | 実装済み | frontend全Nodeテストのグループ化、Python子process未登録検査、workflow負例2件が成功。CI定義のローカル構造検査であり、GitHub Actions実行結果ではない。 |
| 3 clean checkout | 実装・単体検証済み | 隔離Gitで未追跡入力テストが失敗し、追跡fixtureテストが成功。対象commitのclean checkout全品質実行は未実施。未commit差分をcommit証跡へ含めない方針を維持した。 |
| 4 spec必須化 | 実装済み | spec選択9件、Hook回帰20件が成功。`agent:check --phase quick`は終了コード0、受入検査のskipなし。 |
| 5 DB診断・運用文書の整理 | 実装済み・実DB確認は未完 | 診断11件と参照検査1件が成功。configured backend readiness/OS healthもfullで成功。H5-Bの実PostgreSQL suiteは、専用`TEST_DATABASE_URL`と`TEST_RUNTIME_DATABASE_URL`がなく失敗。 |

最終fullレポート`tmp/quality/result.json`は30 task中29 passed、1 failed。失敗は`Acceptance: postgres`のみで、選択235件が専用DB URL未設定によりfixture開始時に失敗した。DBサービスや接続先は自動作成・変更していない。DB非依存backend suiteは992 passed、346 deselected。Node/Python frontend検査、型検査、lint、format、Tooling型検査、Hook検査、生成物照合は成功した。PostgreSQL suiteの出力は構成エラーで、成功またはskipとして数えていない。

後続の判断で、失敗記録の運用機構は今後不要と確認した。規範はbackend設計・validationへ統合済みであり、Git除外の`lessons`資料はクリーンcheckoutに含まれず、必須手順として残すと環境間で不整合になる。そのためルート案内から機構への依存を除き、履歴文書のリンクを現行正本へ置き換え、`.agents/lessons`全体を削除した。追跡対象の規則やアーキテクチャ文書は変更していない。`docs-reference.test.mjs`は現行ガイドのリンクと廃止機構への参照がないことをfullで確認した。

`pnpm agent:check`はCorepackの固定pnpm取得が必要で、通常sandboxではregistry DNSに失敗した。権限付き実行で`pnpm@12.6.0`を使ってquick/fullを完了した。GitHub Actions、実ブラウザ、外部API、本コミットのclean checkoutは未検証。fullはPostgreSQL専用設定がないため終了コード1であり、全検証完了とは扱わない。作業用specと最終レポートを実PostgreSQL完了まで`tmp/quality/`に保持する。

コミット・push・PR作成は実施していない。
