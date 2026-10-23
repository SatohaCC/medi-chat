# LESSON-011: ソース内容の固定ハッシュがWindowsの改行に依存した

- 状態: pending_review
- 作成日: 2026-10-23
- 最終確認日: 2026-10-23
- 承認者・承認日・承認の参照: 未承認
- 更新案の場合の対象: なし
- 統合先・廃止理由: なし

## 本文を読むトリガー条件

テキスト形式の設定・fixtureの固定SHAを追加・変更するとき、またはWindowsで成功しLinux CIでSHAだけが相違したとき。

## 適用する条件／適用しない条件

Git checkoutの改行変換を許容し、テキスト内容を固定する試験に適用する。アップロード原本、署名対象、バイナリ、配布wheelなど実際のbytesが契約となるものは改行を正規化しない。

## 観察した失敗と証拠

PR #61のWindows専用worktreeではDB不要テスト956件が成功したが、Linux CI run 39882667102は955 passed / 1 failedだった。失敗はtest_tc01_single_source_bytes_and_tc03_constructor_ownershipの定義JSONのSHA比較。

<details>
<summary>関連PR・コミットの証拠</summary>

- PR: https://github.com/SatohaCC/medi-chat/pull/61
- 修正コミット: d3edb12
- 対象: backend/tests/integration/test_package_insert_definition_models.py
- Git blobのSHA: d0055d713c4a7365a59b501b0ccaceb62f4b3d082b574dcbbfb80d9bf72f0730
- Windows checkoutのSHA: c283b4d3fef0c022936dfb5154775c88b9c5a1892bb3e1000a8c572e0332f2d0

</details>

## 原因

- 確認できた原因: WindowsのCRLFを含むbytesのSHAを期待値に固定していた。checkoutのCRLFをLFへ変換したbytesはGit blobと完全一致した。
- 未確認の仮説: なし。

## 次回の具体的な確認手順

1. bytes自体の一致か、改行差を許容するテキスト内容の一致かを区別する。
2. 後者ではGit blobとcheckoutの改行差を確認し、LFへ正規化した内容に固定SHAを適用する。
3. LF・CRLF両方で同じ試験が成功し、内容変更では失敗することを確認する。
4. Linux CIの再実行結果を確認し、Windowsだけの成功をCI成功と報告しない。

## 対策の検証

- CRLFをLFへ正規化し、Git blobのSHAを期待値に使用した。
- 関連テスト9件成功。別途、実際の試験関数へLF/CRLFの一時ファイルを渡して両方成功、末尾の内容変更はAssertionErrorになることを確認した。
- Linux CI run 39883428453は成功。DB不要957件、実PostgreSQL225件、静的検査が成功した。
- 実DB・ブラウザ・外部LLMの成功はこの局所検証から主張しない。

## 次の関連作業での評価

未評価。
