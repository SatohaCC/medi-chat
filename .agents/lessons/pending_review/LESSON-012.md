# LESSON-012: 品質入口へ追加した開発ツールが型検査の対象外だった

- 状態: pending_review
- 作成日: 2026-10-24
- 最終確認日: 2026-10-24
- 承認者・承認日・承認の参照: 未承認
- 更新案の場合の対象: なし
- 統合先・廃止理由: なし

## 本文を読むトリガー条件

scripts等の開発ツールへPythonコードを追加・移動する場合、品質入口・CI・hooksの検査範囲を変更する場合、エディタの型エラーとCLIの成功結果が食い違う場合。

## 適用する条件／適用しない条件

対象ディレクトリをinclude・package指定・CLI引数で選ぶ型検査へ適用する。特定ファイルを意図的に対象外とし、その未検証範囲を明示している場合には全体検証成功という結論を要求しない。

## 観察した失敗と証拠

scripts/hooks/quality_gate.pyの同一関数内でresultへCompletedProcessとintを代入していた。エディタはassignment/arg-typeの4件を指摘したが、既存quality:scriptsはlint・format・回帰テストのみで型検査を実行していなかった。

既存のルートPyright includeはbackend、mypyの起動は-p backendだった。mypyへscriptsを明示して直接実行すると4件を再現し、テスト補助のappend戻り値利用も1件検出した。PR・コミットは未作成。

## 原因

- 確認できた原因: 検査コマンドの存在だけを確認し、新しいパスが実際の型検査対象に入ることを確認していなかった。テストとRuffの成功は型検査の代替にならない。
- 未確認の仮説: なし。ユーザーのエディタ設定全体は未調査。

## 次回の具体的な確認手順

1. 計画時に新規・移動先と型検査のinclude/package/CLI引数を照合する。
2. 完了前に対象パスへ一時的な明白な型エラーを入れて、検査が非0になることを確認する。一時ファイルはfinallyで削除する。
3. 修正後は実際の共通入口から実行し、実行計画だけで成功と扱わない。

## 対策の検証

- resultをquick_processとexit_codeへ分離し、型エラーを修正した。
- pnpm typecheck:scriptsでscripts全体のPyright・mypyを実行。ルートtypecheck:pythonとquality:scriptsから呼ぶため、既存CI・Stopの共有経路にも適用される。
- 故意の型エラーをscripts/hooksの一時ファイルへ置き、Pyright・mypyがともに終了1でそのファイルを検出した。削除後は両検査が成功。
- 実行計画の回帰はscripts/checks/quality.test.mjs、hooksの振る舞い回帰はscripts/hooks/test_quality_gate.py。Node 16 passed / Windows対象外2 skipped、Python 8 passed。型検査・lint・format・生成物整合性も成功。
- 証跡: [検証ログ](../../work/20261024-tooling-layout/evidence/hooks-types-validation.log)。GitHub Actions自体やCodexの自動発火はこの修正では再実行していない。

## 次の関連作業での評価

2026-10-24追記（承認待ち）: backend/main.pyのOptional引数についてエディタだけが指摘した報告を受けた。元の式はCLIで再現できず、当該診断の原因は未確定。PostToolUseのquick検査には型検査がなかったため、backend全体のMypyを`--no-incremental`で追加した。ローカルのエディタ設定も環境内Mypyと明示configへ揃えた（`.vscode/`はGit管理外）。

実hookへ一時ファイルのWriteイベントを渡し、`str | None`を`str`引数へ渡すエラーの`[arg-type]`通知を確認、finallyで試験ファイルを削除した。実Mypy検出試験・通知とStopブロックの回帰を追加し、quality:scriptsはNode18 passed/Windows2 skipped、Python10 passed、lint・format・型・生成物検査が成功。Codexアプリでの自動発火や元診断の再現成功とは区別する。承認待ちであり、作業規約やINDEXへは登録しない。
