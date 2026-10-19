# LESSON-009: Windows venvのlauncher PIDをbackend実PIDとして計測しない

- 状態: pending_review
- 作成日・最終確認日: 2026-10-19
- 承認者・承認日・承認の参照: 未承認
- 更新案・統合先: なし

## 本文を読むトリガー条件

Windowsのvenv PythonをPopenで起動し、そのPIDでRSSやnative eventを測る場合。HTTPは成功するのにPID filter後のeventが空になる場合。

## 適用する条件／適用しない条件

実際にlauncherとinterpreterのPIDが分かれる環境に適用する。全OS・全Pythonが二重processになるとは仮定しない。

## 観察した失敗と証拠

Python3.14 venvのPopen.pidとuvicornが記録したos.getpidが異なり、初回2回の性能計測でpool event抽出が空となった。HTTP検索は成功し、実processのcheckout/checkinはログに存在した。これは測定器の欠陥であり、製品のpool漏れ・性能Redとは扱っていない。

- 証拠: `for-llm/progress/20261018-vercel-migration-evidence/pg5/run-01.log`、`run-02.log`と各metricsログ。
- 初回実PIDの終了確認: 同ディレクトリ`initial-owned-process-cleanup.json`。孤児残留は観測していない。
- 修正後: `run-04/measurements.json`、14サンプルの実PID/RSS/所有pool回収を確認。
- PR/commit: 未作成。

## 原因と確認手順

実eventのPIDを取得し、Popen.pid自身またはその子孫であることをOS情報で確認してからRSSを測る。ready後のbaselineも同じ実processから取得する。終了時は捕捉した所有子孫だけを対象にし、port全体や無関係なPythonを終了しない。

## 対策の検証・次回評価

実HTTP/PG14サンプルのpool終了0とRSSを確認。固定LLMと実通信は区別した。別OS/別Python launcherは未実施。次の関連作業での再利用は未評価。承認待ち記録であり規約ではない。
