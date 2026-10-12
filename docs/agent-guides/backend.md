# バックエンド

- 責務・命名・依存方向は[backend/README](../../backend/README.md)の対象節を使う。現在のコードと差分で確認し、既存変更を巻き戻さない。
- Pythonの対象バージョン・Ruff・pytest設定は[backend/pyproject.toml](../../backend/pyproject.toml)。既存パッケージから直接参照し、移動時は相対importの深さと起動点を確認する。
- FastAPI/Pydantic・依存注入・ストリーミングの変更では、適用可能なFastAPI Skillの関連規約を確認する。外部SDKやSQLiteの処理変更は、対象経路の非同期動作・例外・終了処理を受入条件に応じて検証する。
- 添付文書カタログ、検索、Jev、プロンプトの共通定義を変更する場合は[定義ソースの規約](../../backend/infrastructure/package_insert_definitions/README.md)を読む。原文の見出し・本文・出典・改訂情報を保持する。
- 外部LLMの実通信とテストダブルによる検証を区別する。必要な品質コマンドは[validation](validation.md)のPython節を参照する。
