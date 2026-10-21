# LESSON-008: DB移行では文字列の並び順をlocaleと独立に検証する

- 状態: pending_review
- 作成日・最終確認日: 2026-10-19
- 承認者・承認日・承認の参照: 未承認
- 更新案・統合先: なし

## 本文を読むトリガー条件

Python/SQLiteで定めた安定順序をPostgreSQLのORDER BYへ移す場合、または同順位検索の順序が環境で変わる場合。

## 適用する条件／適用しない条件

旧公開契約が文字コード順を持つ場合に適用する。言語ごとの自然な照合順を要求する機能へ機械的に適用しない。

## 観察した失敗と証拠

PG18のlibc/en_US.utf8では、A/B/a/b/亜の順序が既存Pythonのsortedと異なった。医薬品一覧と同順位検索の独立期待で2件のassert Redを確認し、対象ORDER BYの明示C照合で関連35件がGreenになった。3文書だけの初回例は版hashの偶然でGreenとなり、十分な再現例ではなかった。

- 証拠: `for-llm/work/20261018-vercel-migration/evidence/pg4/collation-green.log`、同ディレクトリのcollation Redログ。
- 回帰: `backend/tests/integration/test_postgres_search.py::test_pg028_public_corpus_and_equal_rank_use_legacy_codepoint_order`。
- PR/commit: 未作成。

## 原因と確認手順

DB既定localeの照合とPythonの文字コード順の違い。移行前に同順位の入力と順序を固定し、大小英字と日本語を混ぜ、別hashの版順序も独立して確認する。既定localeを環境で変更するのではなく、契約を所有するクエリの順序を検証する。

## 対策の検証・次回評価

実PGの回帰35件および最終backend全体で確認した。Graphifyだけを依存・順序の証明にしない。別localeを持つ追加PG環境は未実施。次の関連作業での再利用は未評価。承認待ち記録であり規約ではない。
