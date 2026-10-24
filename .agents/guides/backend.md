# バックエンド

- 責務・命名・依存方向は[バックエンド設計](../../docs/architecture/backend-design.md)の対象節を使う。現在のコードと差分で確認し、既存変更を巻き戻さない。
- Pythonの対象バージョン・Ruff・Import Linterは[backend/pyproject.toml](../../backend/pyproject.toml)、pytestの共通設定は[pytest.ini](../../pytest.ini)。既存パッケージから直接参照し、移動時は相対importの深さと起動点を確認する。
- FastAPI/Pydantic・依存注入・ストリーミングの変更では、適用可能なFastAPI Skillおよび`ddd-onion-bestpractices` Skillの関連規約を確認する。Lifespan配線（Composition Root）は`backend/infrastructure/composition/app_lifespan.py`、リクエスト単位の`Depends`関数は`backend/presentation/dependencies.py`、会話ユースケースの束ねは`backend/application/chat/queries/chat.py`（`ChatQueries`）に集約する。外部SDKやPostgreSQLの処理変更は、対象経路の非同期動作・例外・終了処理を受入条件に応じて検証する。
- 添付文書カタログ、検索、Jev、プロンプトの共通定義を変更する場合は[定義ソースの規約](../../backend/infrastructure/package_insert_definitions/README.md)を読む。原文の見出し・本文・出典・改訂情報を保持する。
- 外部LLMの実通信とテストダブルによる検証を区別する。必要な品質コマンドは[validation](../../docs/development/validation.md)のPython節を参照する。
