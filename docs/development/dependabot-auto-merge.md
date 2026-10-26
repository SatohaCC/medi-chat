# Dependabotパッチ自動マージの設定

更新確認はuv・npm・GitHub Actionsとも平日09:00（Asia/Tokyo）。パッチ更新だけを自動マージし、マイナー・メジャー更新は手動確認する。

## 有効化

1. このリポジトリ用のGitHub Appを作成し、このリポジトリにインストールする。
2. AppのRepository permissionsをContents: Read and write、Pull requests: Read and write、Workflows: Read and writeに設定する。WorkflowsはGitHub Actions依存更新のマージに必要。
3. Actionsのrepository variable `DEPENDABOT_MERGE_APP_CLIENT_ID`にAppのClient IDを設定する。
4. Actionsのrepository secret `DEPENDABOT_MERGE_APP_PRIVATE_KEY`にAppの秘密鍵を設定する。
5. リポジトリのAllow auto-mergeを有効化する。
6. mainのbranch protectionでRequire status checksを有効化し、`postgres-contracts`を必須にする。現在のWorkflowはrulesetのみの構成には対応しない。

Appの権限にbranch protectionのバイパスを与えない。未設定・トークン発行失敗・必須CIの保護設定不足ではマージを停止する。GITHUB_TOKENへのフォールバックは行わない。

## マージ後の処理

マージには専用Appのinstallation tokenを使用する。GITHUB_TOKENによるマージではclosed/pushイベントからWorkflowが起動しないため、Neonプレビュー削除とmainのCIを維持するために必要。

PRコードをcheckout・実行せず、App tokenは現在のリポジトリだけを対象に発行する。

## 動作確認

設定後、DependabotのパッチPRで必須CIの完了までマージが保留されること、完了後にマージされること、`Cleanup merged Neon preview branch`とmainのCIが起動することを確認する。マイナー・メジャー更新にはauto-mergeが設定されないことも確認する。

仕様: https://docs.github.com/en/actions/concepts/security/github_token#when-github_token-triggers-workflow-runs
