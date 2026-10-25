# LESSON-015: Reader分離後は実DBテストの注入先も契約別に更新する

- 状態: pending_review
- 作成日: 2026-10-25
- 最終確認日: 2026-10-25
- 承認者・承認日・承認の参照: 未承認
- 更新案の場合の対象: なし
- 統合先・廃止理由: なし

## 本文を読むトリガー条件

Commandの再送ReaderとQueryReaderの分離、Publisherが保持するReaderの差し替え、テストfixtureの依存注入を変更するとき。

## 適用する条件／適用しない条件

同じ具象が複数契約を満たしていた構造を分離する場合に適用する。旧APIの互換メソッドを復活させる根拠にはしない。

## 観察した失敗と証拠

PR #78のコミットe6941ffでPublisher.resultsを更新再送Readerへ変更したが、実PGテストのImportHistoryQueriesと詳細参照に旧注入先が残った。GitHub Actions run40204113965の実PostgreSQL契約は24 failed / 211 passedで、共通エラーはPostgresImportReplayReader.read_resultの位置引数不一致だった。ローカルDB不要1230件の成功ではこの配線を実行していなかった。実PG未実施は報告しており、実PG成功と報告した事実はない。

## 原因

- 確認済み: ファイル移動時のimport更新に比べ、fixtureのReader契約と直接メソッド呼出しの移行確認が不足した。
- 未確認: VercelのResource provisioning failedは別の連携リソース準備失敗であり、本件の原因とは結び付けない。

## 次回の具体的な確認手順

1. 分離前の具象とその属性の全利用を検索し、Command注入・Query注入・直接参照を分類する。
2. テストの実際の組立関数へDB未接続のEngineを渡し、Readerの契約・注入先・公開署名をDB不要層でも確認する。
3. 再送の非復活とQueryのGoneを維持し、実PostgreSQL CIの現在コミットでの結果を確認する。

## 対策の検証

修正前のfixture組立回帰3件がassertion失敗し、QueryReaderへの配線変更後は関連18件が成功。実PostgreSQLの修正後結果はCI待ちであり、最終作業記録で更新する。承認待ち記録でありINDEXへ登録しない。

## 次の関連作業での評価

未評価。
