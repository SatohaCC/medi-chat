# LESSON-018: WorkflowのAPI権限を実際のGITHUB_TOKENで検証する

- 状態: pending_review
- 作成日: 2026-10-26
- 最終確認日: 2026-10-26
- 承認者・承認日・承認の参照: 未承認
- 更新案の場合の対象: なし
- 統合先・廃止理由: なし

## 本文を読むトリガー条件

GitHub ActionsでAPI呼び出しを追加・変更するとき、またはResource not accessible by integrationで失敗したとき。

## 適用する条件／適用しない条件

GITHUB_TOKENの権限を使うWorkflowに適用する。ユーザーのgh認証や専用Appで意図的に管理APIを実行する場合は、別の認証主体として検証する。

## 観察した失敗と証拠

PR #92ではactionlintと模擬GitHub応答の検証が成功したが、実行時のトークン権限を検証できていなかった。パッチ更新PR #97の自動マージは、branchProtectionRuleを取得するGraphQL呼び出しでResource not accessible by integrationとなり、CI成功前に停止した。

- 失敗run: https://github.com/SatohaCC/medi-chat/actions/runs/40340462166
- PR #92: https://github.com/SatohaCC/medi-chat/pull/92
- 修正対象: `.github/workflows/dependabot-auto-merge.yml`

## 原因

- 確認済み: 保護設定取得のAPI呼び出しが実際のGITHUB_TOKENで拒否された。管理者権限での読み取り成功はWorkflow権限の成功を意味しない。
- 別途修正: statusCheckRollupの取得に使うchecks/statusesのread権限も明示されていなかった。この不足による実行失敗は、今回確認した失敗ログでは到達前のため未確認。

## 次回の具体的な確認手順

APIが必要とする権限と認証主体を確認し、不要な管理APIは呼ばない。Workflow変更PRでは、マージ操作を含まない同じ読み取りAPIを実際のGITHUB_TOKENで実行する。模擬応答は分岐検証、実トークンは認証検証として結果を分ける。マージ時の保護はGitHubに適用させ、管理者バイパスを追加しない。

## 対策の検証

- 回帰CI: `.github/workflows/dependabot-workflow-check.yml`で実トークンによるPR・チェック情報の取得を実行する。
- ローカル: 管理API呼び出しを拒否する模擬応答で、成功・CI失敗・必須CI未登録・skip・head変更・マージ拒否などを検証する。
- 実行結果と実マージ・後処理の確認結果は、修正PRの検証欄に記録する。ローカル検証だけでは実マージ成功と扱わない。

## 次の関連作業での評価

未評価。
