# LESSON-004: Windowsの一時ファイルアクセス拒否を業務退行と区別する

- 状態: pending_review
- 作成日: 2026-10-15
- 承認者・承認日・承認の参照: 未承認
- 更新案の場合の対象: なし
- 統合先・廃止理由: なし

## 本文を読むトリガー条件

Windowsで登録・取消・世代取得のpytestを実行し、一時ファイルの
`Path.replace()` / `os.replace()` またはテスト用ファイルの読取が
`PermissionError` / `WinError 5` で失敗した場合。

## 適用する条件／適用しない条件

テスト所有の一時DB・import rootの失敗に適用する。
運用保存先の権限不備や、業務期待値・公開契約の不一致を環境問題として扱う根拠にはしない。
承認待ちの観察記録であり、実装規約ではない。

## 観察した失敗と証拠

医薬品モデル分離の検証で、`test_product_identity_runtime.py` の登録fixtureが
`registration_attempt.py:48` の一時JSON置換で `PermissionError: [WinError 5]` を発生させた。
短い `--basetemp=.tmp/t` / `.tmp/u` でも、異なるケースで再現した。
2回の対象検証はそれぞれ89 passed / 1 failed、16 passed / 1 failed。
失敗は製品同定の期待値検査に達する前の登録IOで発生した。

同じ仮想環境でHEADを別ディレクトリへ展開し、原本・fixtureのコピーを使った
`test_product_identity_runtime.py`、`test_attachment_import.py`、
`test_registration_publisher.py` の比較は48 passed / 2 failed。
保存IOの `ImportStorageError` と、別processの `N.parsed` 読取時の
`PermissionError` を観測した。PRは未作成。

## 原因

- 確認済み: Windowsがテスト用ファイルの置換／読取を拒否した。
- 未確認: ファイルを保持したprocess・セキュリティ製品・OS側の具体的原因。
- パス長だけが原因とは確認できない。短い一時パスでも失敗した。

## 次回の具体的な確認手順

1. chained exceptionまで読み、業務判定の失敗か、その前のIO失敗かを確認する。
2. 作業用のTEMP/TMPと試験専用basetempを使い、同じケースを単独で実行する。
3. 必要ならHEADと同一の原本・fixture・実行環境で比較する。
4. 生存中の試験を止める場合は、今回所有したprocessだけを特定する。
5. 再実行成功で初回失敗を消さず、結果と未確認の原因を分けて報告する。
   原因を確認せずリトライや業務コード変更を導入しない。

## 対策の検証

- 比較で、現行とHEADの双方にテスト用ファイルのアクセス失敗を観測した。
- 医薬品モデル・照合・Reader・DTOの関連検証は別suiteで174 passed。
- OS側の原因解明・対処は未実施。skip/xfailへの変更は行っていない。
- この問題に対する新しい回帰テスト・lint・CIは未導入。

## 次の関連作業での評価

未評価。
