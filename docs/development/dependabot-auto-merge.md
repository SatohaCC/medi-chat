# Dependabotパッチ自動マージの設定

uv・npm・GitHub Actionsの更新確認は平日09:00（Asia/Tokyo）。パッチ更新だけを自動マージし、マイナー・メジャー更新は手動確認する。

## 有効化

mainのclassic branch protectionでRequire status checksを有効化し、`postgres-contracts`を必須チェックに設定する。AppやPAT、追加secretは不要。GitHubのAllow auto-mergeも不要で、WorkflowがCI成功を確認して通常のマージを実行する。現在の保護確認はrulesetのみの構成には対応しない。

既存のNeon削除用variable `NEON_PROJECT_ID`とsecret `NEON_API_KEY`は引き続き使用する。

## 動作

Dependabot作成・同一リポジトリ・main向けのPRを対象に、固定SHAのfetch-metadataでパッチ更新か判定する。PRコードはcheckout・実行しない。

必須CIの保護設定を確認し、最大30分間CIとVercelなどのチェック完了を待つ。`postgres-contracts`の成功と他チェックの成功・中立・skipを確認して、対象head SHAを指定してGITHUB_TOKENでsquash mergeする。失敗したチェックがあれば停止し、headが変わった場合はマージしない。時間切れ・チェック失敗時は原因を解消してActionsから再実行する。

GITHUB_TOKENによるマージではclosed/pushイベントからWorkflowが起動しないため、マージ成功後にmainのCIをworkflow_dispatchで明示実行し、Neon削除Workflowを再利用ジョブとして呼び出す。main CIのdispatchに失敗してもNeon削除ジョブは実行する。手動マージ時は従来のclosedイベントによる削除を維持する。

マージ後に後処理が失敗した場合、当該処理の失敗ジョブを再実行する。

## 動作確認

設定後、パッチPRがCI成功後にマージされ、mainのCIとNeon削除が実行されることを確認する。マイナー・メジャー更新はマージ対象外であることも確認する。

仕様: https://docs.github.com/en/actions/concepts/security/github_token#when-github_token-triggers-workflow-runs
