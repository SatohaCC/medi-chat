# LESSON-017: VercelのPython選択とuv syncの再解決を分けて確認する

- 状態: pending_review
- 作成日: 2026-10-26
- 最終確認日: 2026-10-26
- 承認者・承認日・承認の参照: 未承認
- 更新案の場合の対象: なし
- 統合先・廃止理由: なし

## 本文を読むトリガー条件

Vercelを使うプロジェクトの.python-versionをパッチ固定へ変更するとき。Using Python 3.14の後にuv syncがNo interpreter foundを返すとき。

## 適用する条件／適用しない条件

VercelのPython builderが系列を選択し、同じversion fileをuvが再解決する構成に適用する。ローカル・CIのパッチ固定そのものを禁止する根拠にはしない。

## 観察した失敗と証拠

PR #79、9cd952cのPreviewはUsing Python 3.14 from backend/.python-versionと表示した後、uv sync --active --no-dev --link-mode hardlink --frozen --no-editableがNo interpreter found for Python 3.14.9で失敗した。ローカル3.14.9とGitHub Actionsは成功していた。ビルダーのmajorMinorOnly選択を確認しただけではuvの二段階目の読み込みを保証できなかった。

## 原因

確認済み: Vercelで利用できる系列と、共有.python-versionの厳密なパッチ要求が一致しなかった。ローカルには3.14.9がインストール済みなので、そのままの環境でVercelの未提供interpreter状態を再現したことにしない。

## 次回の具体的な確認手順

1. Vercelの実ログでruntime選択と依存同期を両方確認する。
2. 共有.python-versionは利用できる系列、CIは承認したパッチ版、ローカル初期syncは明示--pythonの形で役割を分ける。
3. 同じパッチ版でのローカル品質結果と、修正コミットのPreviewビルド成功を別々に記録する。

## 対策の検証

root/backendの共有pinを3.14へ戻し、CI3.14.9とローカル実環境3.14.9を維持。root/backend両方のuv起動、uv lock --check、Vercel requirements生成一致、git diff --check成功。修正後の実PreviewとCIはpush後の結果を作業記録で追跡する。

## 次の関連作業での評価

未評価。承認待ち、INDEX未登録。
