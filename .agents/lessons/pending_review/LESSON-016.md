# LESSON-016: Python更新前に.venvのリンク先と所有者を確認する

- 状態: pending_review
- 作成日: 2026-10-26
- 最終確認日: 2026-10-26
- 承認者・承認日・承認の参照: 未承認
- 更新案の場合の対象: なし
- 統合先・廃止理由: なし

## 本文を読むトリガー条件

Python interpreter更新、uv syncによる仮想環境再構築、Windowsの.venv削除権限エラー、pnpm管理からuv管理へ移行するとき。

## 適用する条件／適用しない条件

.venvがSymbolicLink/ReparsePointで共有ストアを参照している場合に適用する。通常のプロジェクト専用ディレクトリへ一律の退避・並行環境を要求しない。

## 観察した失敗と証拠

3.14.0から3.14.9へuv syncした際、backend/.venvがpnpm共有ストアを指していた。uvはリンク先の削除を開始し、Scriptsの削除権限エラーで停止した。元共有環境のLibが欠落しpytestがimportできなくなった。pnpm-workspace.yamlでpython.enabled=falseでも、既存リンクは残存していた。

## 原因

確認済み: 同期前に.venvのLinkType/Targetを確認せず、プロジェクト内の通常ディレクトリだと扱った。未確認: 元共有環境を利用する他の作業の実行状態全体は調査していない。

## 次回の具体的な確認手順

1. interpreter更新前にGet-Item -Forceで.venvのAttributes/LinkType/Targetとpyvenv.cfgを読み、所有範囲を確認する。
2. 共有ストアへのリンクならプロジェクト内のリンクだけを外し、リンク先を再帰削除・移動しない。専用.venvをlocked依存で生成する。
3. 途中失敗で共有先が部分削除された場合は元interpreterと該当lockで復元し、Python版・主要import・依存整合を確認する。

## 対策の検証

リンクだけをRemove-Item（再帰なし）で外し、専用backend/.venvを3.14.9で生成した。元共有環境は明示UV_PROJECT_ENVIRONMENTと元3.14.0、同じuv.lockで101依存を復元し、pytest/sqlalchemy/fastapi/typesafe_sdkのimport成功を確認。共有先を参照していた全プロジェクトのテストは未実施。3.14.9品質結果は作業記録のevidenceを参照。

## 次の関連作業での評価

未評価。承認待ちでありINDEXへ登録していない。
