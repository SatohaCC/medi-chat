# 添付文書の英語名統一

添付文書の英語名を `PackageInsert` / `package_insert` に統一する。2026-11-02のユーザー承認に基づく。

## 対象と保持する語

Domain・Application・Infrastructure・Presentation・frontend・テスト・現行設計文書の名称を揃える。PMDA原本/XML仕様の `<Package>`（22. 包装）、一般的なソフトウェアpackage、原本ファイルとその内容、過去の作業記録は変更しない。

## 外部契約とDB

- 取り込みAPI: `/api/package-insert-imports`（分割アップロードと履歴/結果の下位経路を含む）。
- ブラウザ通知: `package-insert-imported`。画面URL `/imports` と日本語表示は維持する。
- DBテーブル: `package_insert_versions`、`package_insert_assets`、`package_insert_uploads`、`package_insert_upload_parts`。関連する外部キー/索引と新規DB用のAlembic定義も一致させる。
- 保存構造の変換器識別子は `package-insert-domain.v1` とする。encoderとreadinessの判定を一致させ、旧構造の互換読み取りは追加しない。
- 旧APIの別名、旧クラスの再公開、旧DBからの互換移行は設けない。既存DBは旧テーブル名のまま利用できないため、開発DBは原本から新しいschemaへ明示的に再初期化・再登録する。今回のコード変更ではDBの削除・再初期化を実行しない。
- 改名以外の文書構造・原文・出典・改訂・登録/検索の振る舞いは維持する。

## ファイル対応表

以下を改名前の対応表として記録した。ディレクトリ配下の各ファイルを含む。

| 変更前 | 変更後 |
| --- | --- |
| `backend/application/attachment_import/__init__.py` | `backend/application/package_insert_import/__init__.py` |
| `backend/application/attachment_import/commands/__init__.py` | `backend/application/package_insert_import/commands/__init__.py` |
| `backend/application/attachment_import/commands/import_documents.py` | `backend/application/package_insert_import/commands/import_documents.py` |
| `backend/application/attachment_import/commands/models.py` | `backend/application/package_insert_import/commands/models.py` |
| `backend/application/attachment_import/commands/services/__init__.py` | `backend/application/package_insert_import/commands/services/__init__.py` |
| `backend/application/attachment_import/commands/services/import_document.py` | `backend/application/package_insert_import/commands/services/import_document.py` |
| `backend/application/attachment_import/commands/services/import_uploaded_document.py` | `backend/application/package_insert_import/commands/services/import_uploaded_document.py` |
| `backend/application/attachment_import/errors.py` | `backend/application/package_insert_import/errors.py` |
| `backend/application/attachment_import/interfaces/__init__.py` | `backend/application/package_insert_import/interfaces/__init__.py` |
| `backend/application/attachment_import/interfaces/import_execution.py` | `backend/application/package_insert_import/interfaces/import_execution.py` |
| `backend/application/attachment_import/interfaces/import_query_reader.py` | `backend/application/package_insert_import/interfaces/import_query_reader.py` |
| `backend/application/attachment_import/interfaces/import_replay.py` | `backend/application/package_insert_import/interfaces/import_replay.py` |
| `backend/application/attachment_import/interfaces/original_document_registration.py` | `backend/application/package_insert_import/interfaces/original_document_registration.py` |
| `backend/application/attachment_import/interfaces/upload_import_receipts.py` | `backend/application/package_insert_import/interfaces/upload_import_receipts.py` |
| `backend/application/attachment_import/policies.py` | `backend/application/package_insert_import/policies.py` |
| `backend/application/attachment_import/queries/__init__.py` | `backend/application/package_insert_import/queries/__init__.py` |
| `backend/application/attachment_import/queries/dtos/__init__.py` | `backend/application/package_insert_import/queries/dtos/__init__.py` |
| `backend/application/attachment_import/queries/dtos/import_views.py` | `backend/application/package_insert_import/queries/dtos/import_views.py` |
| `backend/application/attachment_import/queries/import_history.py` | `backend/application/package_insert_import/queries/import_history.py` |
| `backend/application/indexing/queries/services/attachment_projection.py` | `backend/application/indexing/queries/services/package_insert_projection.py` |
| `backend/domain/attachment/__init__.py` | `backend/domain/package_insert/__init__.py` |
| `backend/domain/attachment/entities.py` | `backend/domain/package_insert/entities.py` |
| `backend/domain/attachment/exceptions.py` | `backend/domain/package_insert/exceptions.py` |
| `backend/domain/attachment/identifiers.py` | `backend/domain/package_insert/identifiers.py` |
| `backend/domain/attachment/primitives.py` | `backend/domain/package_insert/primitives.py` |
| `backend/domain/attachment/services.py` | `backend/domain/package_insert/services.py` |
| `backend/domain/attachment/value_objects.py` | `backend/domain/package_insert/value_objects.py` |
| `backend/infrastructure/document_import/attachment_contracts.py` | `backend/infrastructure/document_import/package_insert_contracts.py` |
| `backend/infrastructure/document_import/attachment_payloads.py` | `backend/infrastructure/document_import/package_insert_payloads.py` |
| `backend/infrastructure/persistence/mappings/attachment_document_mapping.py` | `backend/infrastructure/persistence/mappings/package_insert_document_mapping.py` |
| `backend/infrastructure/persistence/schemas/attachment_tables.py` | `backend/infrastructure/persistence/schemas/package_insert_tables.py` |
| `backend/presentation/attachment_import_models.py` | `backend/presentation/package_insert_import_models.py` |
| `backend/presentation/attachment_import_routes.py` | `backend/presentation/package_insert_import_routes.py` |
| `backend/tests/application/attachment_import/test_registration_values.py` | `backend/tests/application/package_insert_import/test_registration_values.py` |
| `backend/tests/application/indexing/test_active_attachment_projection.py` | `backend/tests/application/indexing/test_active_package_insert_projection.py` |
| `backend/tests/application/indexing/test_attachment_projection.py` | `backend/tests/application/indexing/test_package_insert_projection.py` |
| `backend/tests/domain/attachment/test_attachment_content.py` | `backend/tests/domain/package_insert/test_package_insert_content.py` |
| `backend/tests/domain/attachment/test_attachment_domain.py` | `backend/tests/domain/package_insert/test_package_insert_domain.py` |
| `backend/tests/domain/attachment/test_attachment_latest_revision.py` | `backend/tests/domain/package_insert/test_package_insert_latest_revision.py` |
| `backend/tests/domain/attachment/test_attachment_registration_domain.py` | `backend/tests/domain/package_insert/test_package_insert_registration_domain.py` |
| `backend/tests/domain/attachment/test_attachment_value_contracts.py` | `backend/tests/domain/package_insert/test_package_insert_value_contracts.py` |
| `backend/tests/domain/attachment/test_attachment_value_objects.py` | `backend/tests/domain/package_insert/test_package_insert_value_objects.py` |
| `backend/tests/domain/attachment/test_reference_integrity.py` | `backend/tests/domain/package_insert/test_reference_integrity.py` |
| `backend/tests/infrastructure/persistence/test_attachment_document_mapping.py` | `backend/tests/infrastructure/persistence/test_package_insert_document_mapping.py` |
| `backend/tests/infrastructure/pmda_xml/test_attachment_xml_decoder.py` | `backend/tests/infrastructure/pmda_xml/test_package_insert_xml_decoder.py` |
| `backend/tests/integration/test_attachment_import_search_isolation.py` | `backend/tests/integration/test_package_insert_import_search_isolation.py` |
| `backend/tests/integration/test_attachment_import_workers.py` | `backend/tests/integration/test_package_insert_import_workers.py` |
| `backend/tests/presentation/test_attachment_import_http.py` | `backend/tests/presentation/test_package_insert_import_http.py` |
| `backend/tests/presentation/test_attachment_input_validation.py` | `backend/tests/presentation/test_package_insert_input_validation.py` |
| `backend/tests/support/attachment_import_e2e_server.py` | `backend/tests/support/package_insert_import_e2e_server.py` |
| `backend/tests/support/attachment_import_fixtures.py` | `backend/tests/support/package_insert_import_fixtures.py` |
| `docs/development/attachment-import.md` | `docs/development/package-insert-import.md` |
| `frontend/features/attachment-import/api/attachmentImport.ts` | `frontend/features/package-insert-import/api/packageInsertImport.ts` |
| `frontend/features/attachment-import/components/ImportHistory.styles.ts` | `frontend/features/package-insert-import/components/ImportHistory.styles.ts` |
| `frontend/features/attachment-import/components/ImportHistory.tsx` | `frontend/features/package-insert-import/components/ImportHistory.tsx` |
| `frontend/features/attachment-import/components/ImportScreen.styles.ts` | `frontend/features/package-insert-import/components/ImportScreen.styles.ts` |
| `frontend/features/attachment-import/components/ImportScreen.tsx` | `frontend/features/package-insert-import/components/ImportScreen.tsx` |
| `frontend/features/attachment-import/hooks/useAttachmentImport.ts` | `frontend/features/package-insert-import/hooks/usePackageInsertImport.ts` |
| `frontend/features/attachment-import/hooks/useImportHistory.ts` | `frontend/features/package-insert-import/hooks/useImportHistory.ts` |
| `frontend/features/attachment-import/index.ts` | `frontend/features/package-insert-import/index.ts` |
| `frontend/features/attachment-import/model/attachmentImport.ts` | `frontend/features/package-insert-import/model/packageInsertImport.ts` |

## 検証

backend/frontend/scriptsの品質ゲート、取り込みAPIと登録・検索の既存回帰試験、frontendビルド、モックブラウザの取り込み/履歴/分割アップロード試験で利用側を確認する。実DB・原本・実ブラウザ接続の未実施は完了報告で区別する。

### 2026-11-02の検証結果

- `pnpm quality:backend`: 成功。通常テスト953件成功・実DB/非公開原本等345件除外、Import Linter 24契約、Domain/Application/Infrastructure構造検査、構造ハーネス66/73/42件、Pyright・mypy・Ruff確認を含む。
- `pytest`のOpenAPI比較・Import Linterルール検出能力・アーキテクチャ依存検査: 139件成功。先行するエージェント導入で試験用package一覧に不足していた `agent` も実構成に合わせた。禁止契約やignoreを緩和していない。
- `pnpm quality:frontend`: 全体では不成功。今回未変更でHEADと一致する `features/chat/hooks/useEvidencePanelState.test.mjs` のlint/整形と `styles/README.md` の整形が既存の失敗。変更した19ファイルのBiome check、StyleX lint、TypeScript、frontend単体121件は成功。
- `pnpm --filter frontend exec playwright test e2e/imports.spec.ts e2e/import-history.spec.ts e2e/segmented-upload.spec.ts`: モックChromium 11件成功。原本byte列を維持した10MiB分割転送、取り込み後の履歴更新、モバイル表示、失敗後の再試行を確認。実backend/DBへの接続成功を意味しない。
- `pnpm build`（`MEDI_CHAT_NEXT_DIST_DIR=.next-e2e-build`）: 成功。通常の開発出力と分離した。
- `pnpm quality:scripts`: 終了コード0。Node試験18件成功・既存のシグナル試験2件skip、hook試験14件成功、型/lint/整形・Vercel依存・検索ガイド生成物の一致を確認。skipを成功件数に含めない。
- DB接続なしでPostgreSQL方言のDDLを11テーブル分コンパイル。改名対象4テーブルの名称と参照解決を確認。実PostgreSQLへのmigration/登録・通常設定での起動・実LLM・実backend接続のブラウザ試験は未実施。
- 対応表61ファイルの移動先存在・移動元不在、コード/設定内の旧名称が残っていないこと、PMDA XMLの `<Package>` と原本名 `attachment-XML.xsd` の保持を確認。
