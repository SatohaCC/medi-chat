# 改訂年月による添付文書選択の変更と検証

2026-10-16。YJコードごとの公開添付文書を、登録順から原本の改訂年月で選ぶ方式へ変更。

## 変更

- `AttachmentRegistration` と、登録提案・受付履歴のDomain型、登録台帳Repositoryを廃止。
- `RegistrationVersion` は文書版・対象YJ・改訂年月を持つ値とし、ファイル所有を分離。
- `latest_attachment()` は新しい年月を選択。同原本は再利用し、同年月の別原本は競合。
- Applicationで原本の改訂一覧から最大の `YYYY-MM` を取得する。日・版番号・登録順を補完しない。
- 古い文書を後から登録しても公開先と検索世代を戻さない。複数YJは各YJで独立に比較。
- 同年月競合はHTTP 409 `same_revision_conflict`、改訂年月欠落は422 `missing_revision`。
- 初期登録CLIも同じポリシーで、入力順によらず最新を選び、返却順は入力順を保持。
- receipt、受付番号、所有manifest、旧版と世代のlease保護・cleanupは永続化側に保持。
- 起動・read-only snapshot検証も改訂規則を確認する。不一致は
  `revision_policy_migration_required` とし、起動時にDBを自動変更しない。
- 保存schema・OpenAPIの変更、運用DB・原物の更新は実施していない。

## 検証

実行はリポジトリroot、既存の `backend/.venv/Scripts/python.exe` を使用。
実SQLite・HTTP・OS processの試験は試験専用TEMP/TMP・basetempで実行し、
子processを含め `PYTHONUTF8=1` に統一した。外部LLM実通信・ブラウザE2Eは未実施。

- 新しい改訂選択、公開・HTTP・旧DB拒否、原本版IDのsuite: **18 passed**。
- 更新した登録・公開・再送・lease・初期登録CLIの先行検証: 63 passed / 3 failed。
  期待改訂年月の更新漏れ1件を修正。残り2件はWindows一時ファイルアクセス拒否。
- backend全体: **1080 passed / 49 failed**、4 subtests passed。
  全体成功ではない。この実行には後続のfixture修正前と文字コード不一致のケースを含む。
- 全体の失敗から以下の既存12件を除いた37件を再検証: **36 passed / 1 failed**。
  残りの登録API全フィールド契約は500だったが、単独再検証は **1 passed**。
  初回失敗を取り消して全体成功とは扱わない。
- 実OS suiteの再検証: 8 passed / 1 failed。4つのクラッシュ回復ケースは通過。
  失敗は別のfixture登録時に `registration_attempt.py` の `os.replace()` が
  `PermissionError: [WinError 5]` を発生したもの。OS側原因は未確認。
- Ruff check、Import Linter 6契約、Pyrightは通過。
- 現行とHEADの `create_app().openapi()` は別processで比較して完全一致。

全体実行時は標準出力だけのUTF-8指定が親processのCP932復号と不一致になり、
Import Linterの子process試験25件が失敗した。
`PYTHONUTF8=1` に揃えた単独suiteは **25 passed**。制約設定は変更していない。

HEADのコードを独立ディレクトリへ展開し、同じ原本・fixtureのコピーで比較したsuiteは
**68 passed / 12 failed**。既存の不一致は次のとおり。

- OpenAPIと保存済み期待値: 1件（現行とHEAD自体のOpenAPIは一致）。
- XML decoderと保存済み期待値: 7件。
- 公開応答と保存済み期待値: 1件。
- 既存FTSのDDL許可構造検査: 3件。

backend全体のformat確認は今回未変更の9ファイルで失敗。担当外の整形は行っていない。
Windowsの登録IOに関する既存の観察は
`agent-lessons/pending_review/LESSON-004.md` にあるが、未承認のため規約としては適用していない。

## 運用への適用

既存DBの公開先が改訂年月の最大値と一致しない、改訂年月が欠落、または最新年月の原本が
複数ある場合は、運用writer停止・backupと復元検査後に原本を確認し、別の準備済みDBへ
`initialize_registrations` CLIで明示的に初期登録・検証する。
最新原本が以前のcleanupで削除済みなら再取得が必要。同年月競合は自動で解消しない。
この作業では運用DBの移行を実行していない。
