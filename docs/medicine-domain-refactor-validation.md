# 医薬品・添付文書の責務分離の検証

検証日: 2026-10-15。医薬品名称・別名生成・優先度選択をmedicineへ移し、
文書参照をattachment、両者の結合と検索対象決定をApplicationへ分離した差分が対象。
DBスキーマ・保存形式・公開JSON・運用索引は変更していない。

## 通過した検証

- 関連suite: 174 passed。アーキテクチャ、Applicationポート、カタログ、
  新しい照合ポリシー、製品同定の純粋規則・取得、候補提示、非同期Reader、
  公開DTO往復、名称正規化を含む。実SQLiteを使うケースと固定外部SDKダブルを区別する。
- 新規ポリシーテスト: 上記に含まれる5件。文書非依存、別名・優先度、
  同一YJの複数文書、未同定入力の文書fallback、同点候補・言及順を確認。
- Ruff check: 通過。
- Import Linter: 6契約通過。
- Pyright: 0 errors / 0 warnings。
- 変更したPythonファイル60件のformat確認と `git diff --check`: 通過。
- 現行とHEADの `create_app().openapi()` を別processで比較し、完全一致。

標準コマンドは `docs/agent-guides/validation.md` を参照。
uvのキャッシュアクセス拒否後、既存の `backend/.venv/Scripts/python.exe` を直接使用した。
SQLiteを使う検証はサンドボックス外、試験専用TEMP/TMP・basetempで実行した。
実LLM通信・ブラウザE2E・運用DBの更新は行っていない。

## 全体回帰の失敗と比較

全体実行は1123 passed / 18 failed、4 subtests passed、警告1件。
全体成功ではない。skip/xfailへ変更したケースはない。

失敗12件はHEADを別ディレクトリに展開し、同じ原本・fixtureのコピーで再現した。

- OpenAPIと保存済み期待値の不一致: 1件。
- XML decoderと保存済み期待値の不一致: 7件。
- 公開応答の保存済み期待値との不一致: 1件。
- 既存FTSのDDL許可構造検査: 3件。

このHEAD比較suiteは68 passed / 12 failed。今回の範囲外の期待値・構造検査は変更していない。

残る6件は全体実行後に単独再検証し、6 passed。
1件は、全体suite収集後に更新したReader投影の純粋型検査。
5件は登録fixtureのIO失敗、または指定faultより先にartifact phaseで失敗したケース。
現行でWindows一時JSONの `os.replace()` によるアクセス拒否を観測した。
HEADの登録・取消比較も48 passed / 2 failedで、保存IOと試験用ファイル読取の失敗を観測した。
再実行成功は初回失敗を打ち消さず、OS側の具体的原因は未確認。

backend全体のformat確認は、今回未変更の9ファイルが現在のRuff設定で整形対象となり失敗。
担当外の整形は行っていない。

登録IOの観察は `agent-lessons/pending_review/LESSON-004.md` に承認待ちとして記録した。
