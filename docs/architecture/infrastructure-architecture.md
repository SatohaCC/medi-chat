# Infrastructureハーネス

## 目的と対象

`scripts/checks/infrastructure_architecture.py` が `backend/infrastructure/` 配下のディレクトリ構造・命名・依存方向・公開範囲、および Repository / ORM / Core Table の責務境界を静的に検査する。検査対象のソースコードは AST として解析し、実行時コードの import や実行は行わない。標準の backend lint（`pnpm --filter backend lint`）および CI で全規則を強制する。違反 baseline や個別ファイルの抑制設定は設けない。

DDD / Onion アーキテクチャに基づき、技術的関心事をアダプタとして外層に分離し、Domain / Application からの逆依存を防止するとともに、アダプタ間の不要な結合を排除する。

## 配置と責務

### 1. アダプタ一覧

`backend/infrastructure/` 直下には各技術基盤に対応するアダプタパッケージ、および配線・起動を担うパッケージのみを配置する。直下の単独 Python ファイル（`__init__.py` を除く）は禁止する。

```text
backend/infrastructure/
  persistence/                 # PostgreSQL永続化（サブパッケージに階層化）
  document_import/             # アダプタ間ドキュメント取り込み契約・Payload
  serialization/               # アダプタ非依存のシリアライズ・Payload Codec
  llm/                         # LLMプロバイダ基盤
  intent/                      # 意図分類アダプタ
  morphology/                  # 形態素解析アダプタ
  pmda_xml/                    # PMDA XML解析・変換
  sources/                     # 外部データソース読み取り
  authentication/              # 認証トークン・クレデンシャル検証
  package_insert_definitions/  # 添付文書定義・設定
  composition/                 # Composition Root（アプリケーション全体の具象配線）
  cli/                         # 管理・検証用CLIツール群
```

### 2. persistence の内部構造

永続化アダプタ `persistence/` は、責務に応じて以下のサブパッケージに役割を分離する。

```text
backend/infrastructure/persistence/
  schemas/                     # SQLAlchemy Core Table / MetaData のみ
  stores/                      # 更新・セッション・row lock保持ストア（postgres_*_store.py）
  queries/                     # 参照系クエリ・スナップショット（postgres_*_query_reader.py, postgres_*_snapshot_provider.py）
  registration/                # 添付文書登録発行・再読込（postgres_*_publisher.py, postgres_*_replay_reader.py）
  records/                     # 共通DBレコード読み取り（postgres_*_records.py）
  mappings/                    # DBレコードとモデル・DTOの変換（*_mapping.py）
  runtime/                     # DBエンジン・接続準備・ワーカー管理（postgres_*.py, *_workers.py）
  maintenance/                 # DBメンテナンス・クリーンアップ（postgres_*_cleanup.py）
```

- **repositories/ および models/ について**: 本リポジトリでは現在、Domain集約のRepository契約およびORM（Declarative Base / Mapped）は導入していないため、空ディレクトリや形だけの配置は行わない。将来導入される場合は、Repository は必ず Domain 集約プロトコルを実装し、models は ORM mapped class 専用とする。

### 3. 命名規則

- 全モジュールファイル名はスネークケース（`snake_case`）とし、対象語と技術役割を明示する。
- `utils.py`, `helpers.py`, `common.py`, `base.py`, `models.py`, `interfaces.py`, `service.py` などの汎用的な名称は一律禁止する。
- 各アダプタの具象実装には、役割を表す接尾辞（`provider`, `classifier`, `extractor`, `decoder`, `parser`, `encoder`, `mapping`, `settings`）を付与する。
- persistence以外は平坦なpackageとする。TOMLの`roles`は既存moduleの役割名であり、下位directoryの許可ではない。新しいsubjectにも、`_provider`, `_classifier`, `_extractor`, `_extraction`, `_decoder`, `_parser`, `_encoder`, `_mapping`, `_settings`, `_reader`, `_assembly`, `_tokens`, `_credentials`, `_lifespan`, `_composition`, `_codec`, `_renderer`, `_values`, `_payloads`, `_contracts`, `_transformer`, `_builder`, `_probe`, `_errors`, `_messages`, `_base`, `_factory`, `_stream`, `_adapter`を適用する。例えば`llm/new_provider.py`は許可し、`llm/banana.py`と任意の深階層は拒否する。CLIはcheckerの`CLI_NAMES`に定義した既存のコマンド語彙に限る。

## 依存と公開範囲

### 1. インポート規則

- Infrastructure 内の import は、常に `backend.` から始まる絶対 import とする。相対 import（`.` や `..`）および wildcard import（`from ... import *`）は禁止する。
- 各パッケージの `__init__.py` は空または docstring のみとし、シンボルの再公開（re-export）や初期化処理の記述を禁止する。旧モジュールを薄い再公開ラッパーとして残すことも禁止する。
- `importlib`, `__import__`, `eval`, `exec` 等を用いた動的なインポートや境界バイパスは禁止する。

### 2. レイヤ間・アダプタ間の依存規則

- **Onion / DDD 原則**: Domain および Application から Infrastructure への逆依存は禁止する。Presentation から通常アダプタへの直接依存も禁止し、Composition Root（`composition/`）を経由して具象インスタンスを配線する。
- **アダプタ間独立規則**:
  - `llm`, `intent`, `morphology`, `pmda_xml`, `authentication`, `sources` は相互に独立しており、依存を禁止する。
  - `persistence` は上記のアダプタに依存しない。アダプタ間の連携は `document_import` の Protocol や `package_insert_definitions` の設定定義を介して行う。
  - `serialization` および `document_import` は他の技術アダプタに依存しない。
- **persistence 内部の依存方向**:
  - `schemas` および `runtime` は上位の役割（`queries`, `stores`, `registration`, `maintenance`）に依存しない。
  - `mappings` は `schemas`, `queries`, `stores`, `registration` に依存しない。
  - `records` は Application Query DTO / Command 復元に直接依存しない。
  - `queries`, `stores`, `registration` 相互間の直接依存は禁止する（例: 登録 Publisher は Query アダプタを利用せず、専用の再読込 Reader または Records を利用する）。

### 3. 公開モジュールと consumer 境界

各アダプタが外部へ公開するモジュール・公開シンボル、およびそれを import 可能な consumer は `backend/infrastructure-architecture.toml` に明示的に定義する。

- **通常 consumer**: アプリケーション本体の起動・配線を担う `composition`、および各種管理 CLI（`cli`）。
- **限定公開（U1 / U2）**:
  - **U1**: `backend/migrations/postgres/env.py` に対する `runtime/postgres_engine.create_postgres_engine` の公開。
  - **U2**: `backend/infrastructure/cli/manage_postgres.py` に対する `pmda_xml/xml_safe_parser.parse_source`、`registration_payloads.{FigureInput, PostgresRegistrationInput}`、`attachment_document_mapping.document_from_payload`、`search_projection_mapping.projection_records` の管理目的の限定公開。
- 公開モジュールであっても、定義された公開シンボル以外の非公開シンボルや private ヘルパーの利用は禁止する。
- テストコード（`backend/tests/`）からの import は許容するが、テストでの利用を理由に本番公開へ昇格させてはならない。

## 検査規則一覧

| 規則ID | 内容 |
| --- | --- |
| **INF000** | Python 構文エラーの検出 |
| **INF001** | 未宣言アダプタ、禁止配置、スネークケース違反、汎用ファイル名、persistence 役割配置違反 |
| **INF002** | 相対インポート（`from .` / `from ..`）の禁止 |
| **INF003** | ワイルドカードインポート（`from ... import *`）の禁止 |
| **INF004** | `__init__.py` の再公開・コード記述禁止、再公開専用モジュールの禁止 |
| **INF005** | Domain / Application / Presentation から Infrastructure への逆依存、Infrastructure から Presentation への逆依存 |
| **INF006** | アダプタ間の禁止依存方向、persistence 内部の役割間禁止依存方向 |
| **INF007** | 非公開モジュール・非公開シンボルの利用、未許可 consumer からの利用 |
| **INF008** | モジュール間循環依存（アダプタ内・アダプタ間の DAG 検証） |
| **INF009** | `importlib`, `__import__`, `eval`, `exec` 等による動的 import・実行バイパスの禁止 |
| **INF010** | Repository プロトコル未実装、ORM mapped class 以外の models 配置、schemas 以外での Core Table 定義 |

## AST 静的解析の特性と検証

- **静的検査の範囲**: AST 解析により、静的な import、エイリアス、クラス・関数定義、デコレータ、型注釈を安全に検証する。検査対象コードを実行しないため、副作用や環境依存を招かない。
- packageからのmodule importとmodule aliasの属性参照も解決する。RepositoryはDomainの`repositories.py`に定義されたProtocolの継承を確認し、名前が`Repository`で終わるだけでは許可しない。ORMはSQLAlchemyのDeclarativeBaseまたはregistryのmapped decoratorを識別し、同じfileの通常クラスも個別に拒否する。Alembic入口はattachment/authentication両方のTable正本を読み込み、共有MetaDataを登録する。
- **解析の限界**: 静的構文解析では、集約のビジネス意味論、実行時 SQL の業務的妥当性、動的リフレクションの完全追跡はカバーできない。
- **補完手段**:
  - 静的型検査（Pyright / Mypy）
  - Import Linter 契約（`backend/pyproject.toml`）
  - DB 非依存の高速テスト（`pytest backend/tests -m "not postgres and not source_data"`）
  - 実機 PostgreSQL 結合テスト（`pytest backend/tests -m "postgres"`）
  - CLI `--help` 動作確認
