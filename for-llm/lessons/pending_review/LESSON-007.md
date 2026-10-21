# LESSON-007: Playwrightの共通出力先を複数の実行で共有しない

- 状態: pending_review
- 作成日: 2026-10-18
- 最終確認日: 2026-10-18
- 承認者・承認日・承認の参照: 未承認
- 更新案の場合の対象: なし
- 統合先・廃止理由: なし

## 本文を読むトリガー条件

複数のPlaywrightコマンドを並列実行する場合、またはtrace保存中にENOENTが発生した場合。

## 適用する条件／適用しない条件

独立したPlaywright実行が同じoutputDirを使用する場合に適用する。同一実行のworker並列化とは区別する。

## 観察した失敗と証拠

全体レビュー中、実接続E2Eと追加のモックE2Eを並列実行した。
`frontend/playwright.config.ts`と`frontend/playwright.import-integration.config.ts`はoutputDirを分離しておらず、既定の`frontend/test-results`を共有した。
実接続側のtrace記録・コピーで`.playwright-artifacts-0`配下のENOENTが発生した。
該当実行の証跡ファイルエラーを製品不具合の根拠から除外し、追加モック実行を終了した。

## 原因

- 確認済み: 独立した実行が既定の出力先を共有していた。
- 推定: 一方の実行開始時の出力先清掃により、他方の記録中ファイルが失われた。
- 未確認: 個々の削除操作の実行主体は追跡していない。

## 次回の具体的な確認手順

1. 実行前にoutputDir・サーバーポート・Next出力先を確認する。
2. 独立したE2Eは直列実行する。並列が必要なら`--output`も実行ごとに分ける。
3. ENOENTをアプリの退行と判定せず、競合を除いた単独実行で再確認する。

## 対策の検証

- 実施: 追加モック実行を停止し、TC137を単独で再実行。
- 単独再実行: `pnpm --filter frontend exec playwright test --config=playwright.import-integration.config.ts --grep TC137 --timeout=30000`は1件失敗。placeholderを探す`locator.fill`で停止し、証跡ファイルのENOENTは再現しなかった。標準120秒の再実行ではない。
- 当初のモック実行は途中終了であり、未実施ケースを成功扱いしない。
- 当初のレビュー段階では共通設定・本番コード・テストコードを変更していない。
- 後続の修正依頼で、モックのoutputDirを`test-results/mock`、実接続を`test-results/real`へ分離した。サーバーポートとNext出力先も別であることを確認し、全体ゲートでは直列実行する。
- この記録自体は引き続き承認待ちとする。
- 最終確認: `pnpm test:e2e`が終了コード0。設定先DBの起動確認、モック68件、実API/DB接続2件が通過し、証跡保存のENOENTは発生しなかった。外部SDKは固定ダブルであり、外部LLMへの実通信は対象外。

## 次の関連作業での評価

未評価。承認待ちの観察記録であり、規約として扱わない。
