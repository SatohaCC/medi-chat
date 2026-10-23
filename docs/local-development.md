# ローカル開発

コマンドはリポジトリルートから実行します。Node.js 24.22.1（`.nvmrc`）・pnpm（`package.json`）、Python 3.14以上・uv、Docker Desktopを用意してください。

## セットアップ

```bash
pnpm install --frozen-lockfile
uv sync --project backend --locked --group dev
```

JavaScript依存はpnpm、Python依存はbackendのuvで管理します。pnpmによるPython環境管理は無効です。
`.env.example`を参考に`.env.local`を作成し、PostgreSQLの接続先と利用するLLMのAPIキーを設定します。実際の接続情報はGitへ追加しません。

## ローカルPostgreSQLの準備

通常backendはPostgreSQLだけを使用します。原XML・図のbytes、完全な文書構造、検索投影、登録結果をDBで保持し、起動時に入力ディレクトリを読みません。

1. Docker Desktopを起動し、rootの`.env.postgres.example`を`.env.postgres`へコピーして管理・migration owner・runtimeの別々のパスワードを設定します。`docker compose --env-file .env.postgres up -d --wait`でPostgreSQL 18をloopback `127.0.0.1:15432`に起動します。
2. fresh named volumeの初回だけ`scripts/postgres/init.sh`が`medi_chat_dev`/`medi_chat_test`と`medi_chat_owner`/`medi_chat_app`を作ります。両roleは非superuser・DB/role作成不可、ownerだけがschema DDLを担当し、runtimeはDMLを使います。既存volumeでは初期化scriptは再実行されません。既存DBを初期化するためのvolume削除は行わないでください。
3. `.env.example`のPG URL例に従い、owner/runtime/testの接続先をローカル環境変数へ設定します。パスワードはURL encodeします。管理者接続はアプリへ渡しません。CLIの`--database-env`はURLを保持する環境変数名を明示します。
4. owner URLを`MEDI_CHAT_MIGRATION_DATABASE_URL`へ設定し、rootから`pnpm db:migrate`を明示実行します。接続URLをコマンド引数へ貼り付ける必要はありません。通常起動・publisherはDDLを実行しません。
5. `pnpm db:initialize`で空DBへXML/図を登録します。図の参照先欠損/危険path/symlinkを含む初期登録は拒否し、非空DBは置換しません。既存原本・SQLite・生成物は保持します。
6. 保持原本の明示exportは同CLIの`export --version-id <document_id:sha256> --output-dir <新規出力先>`、清掃は`maintenance`です。exportは`source.xml`と`figures/`へ元bytesを出し、stdoutに元filename/hash/byte数を返します。清掃後はtombstoneだけを保持し、旧版再送でpayloadを復活させません。

通常のローカルテストにはPostgreSQLもテスト用の認証情報も不要です。上記のローカルPostgreSQLはアプリの開発起動に使います。実PG試験はGitHub Actionsの専用`medi_chat_test`で実行し、各試験は`medi_chat_test_<run>`schemaだけを作成・削除します。接続情報をログや共有文書へ貼り付けないでください。

CIの`Synthetic PostgreSQL contracts`は、DB不要のテストと、job所有のPG18 service・非superuser owner/runtime・UUIDschemaを使う合成XMLの実DBテスト全体、静的ゲートを実行します。`source_data`で分類したGit管理外の原本・生成物が必要な試験はCI対象外です。原本集合は配布・自動取得せず、原本を使う試験・実ブラウザ・性能はデータと必要な実行環境を準備して別に検証します。

## 起動

DBのマイグレーション・初期登録を済ませてから起動します。

```bash
pnpm dev
```

フロントエンドは http://localhost:3000 、バックエンドは http://localhost:8000 です。個別に起動する場合は `pnpm dev:frontend` / `pnpm dev:backend` を使います。
通常起動時にはDDL・原本の初期登録・索引の再構築を実行しません。

## 検証

| コマンド | 内容 |
| --- | --- |
| `pnpm lint` | frontend・backendのlintと依存検査 |
| `pnpm typecheck` | TypeScript・Pyright・mypy |
| `pnpm test:backend` | DB不要のbackendテスト（ローカル標準） |
| `pnpm test:postgres` | 合成データによる実PostgreSQLテスト（GitHub Actions） |
| `pnpm test:e2e` | 通常設定の起動確認とブラウザテスト |
| `pnpm build` | frontendのビルド |

`pnpm check`と`pnpm format`はファイルを変更します。検証だけを行う場合はlint・型検査を使います。
通常の`pytest`も実DBテストを除外します。ローカルではdotenv・APIキー・DB認証を隔離し、SQLAlchemyの実接続を拒否します。DB不要のテストは既存のFake・固定ダブルを使い、SQLite用の代替実装は追加しません。

`pg_engines`に直接・間接依存する試験は`postgres`に自動分類します。fixtureを介さず実DBへ接続する試験には`@pytest.mark.postgres`を付けます。原本・生成物が必要な試験には`@pytest.mark.source_data`を付けます。

実DBの明示実行は`pytest --postgres`で有効になり、`TEST_DATABASE_URL` / `TEST_RUNTIME_DATABASE_URL`の不足・接続エラーは失敗とします。`pnpm test:postgres`はさらに`postgres and not source_data`を選択します。DB不要の合成データ試験だけなら`pnpm test:backend -m "not source_data"`を使います。原本を含む実DB試験は`pytest --postgres -m source_data`で別途選択します。除外件数を成功件数に含めないでください。

E2Eの通常設定・モック・実接続の違いは[検証ガイド](../for-llm/guides/validation.md)を参照してください。

## データと運用

- [添付文書の取り込み・登録](attachment-import.md)
- [PMDA原本とオフライン変換](../data/pmda/README.md)
- [DB運用・マイグレーション・再構築](backend-design.md#データベース運用とマイグレーション)
- [Vercel・Neonへのデプロイ](vercel-deployment.md)
