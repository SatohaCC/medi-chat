# Vercel向けのDB・XML取り込み準備

## 保存先

ローカルはDockerのPostgreSQL、デプロイ先はVercel Marketplace経由のNeon PostgreSQLを使用する。原本XML・図・構造・検索投影・アップロード中の分割データをPostgreSQLへ保存し、BlobやFunctionのローカルディスクを要求しない。

## リポジトリのデプロイ構成

ルートの`vercel.json`でVercel Services（Beta）を宣言する。VercelでGitリポジトリをImportするときは、Root Directoryをリポジトリ直下（`.`）にする。Dashboard側に単一アプリ向けのBuild CommandやOutput Directoryを上書き設定しない。

| Service | 基準ディレクトリ | 起動入口／framework |
| --- | --- | --- |
| backend | `.` | FastAPI、`backend.main:app` |
| frontend | `frontend` | Next.js |

`/api`・`/api/*`・`/health`・`/ws/chat`をバックエンド、それ以外をフロントエンドへ振り分ける。パスは維持される。WebSocketの`/api/ws`もこの経路を使う。ブラウザからは同じドメインへ接続するので、デプロイ時の`NEXT_PUBLIC_API_URL`・`NEXT_PUBLIC_WS_URL`は未設定にする。

Node.jsはルートとfrontendの `package.json` にある `engines.node: "24.x"` で指定する。Vercelはメジャーバージョン単位で選択し、マイナー・パッチは自動更新するため、24.22.1への厳密な固定はできない。既存Project SettingsのNode.js Versionも24.xに揃え、次回デプロイのビルドログで実際のバージョンを確認する。
ローカルとCIはルートの `.nvmrc` にある24.22.1を使用する。nvm-windowsでは `nvm install 24.22.1`、`nvm use 24.22.1` を実行する。

Pythonはルートの`.python-version`で3.14を指定する。`requirements.txt`はVercelが基準ディレクトリから読めるruntime依存ファイルで、`backend/uv.lock`から生成する。開発依存は含めず、手編集しない。

```powershell
pnpm vercel:requirements        # Python依存を変更したときに再生成
pnpm vercel:requirements:check  # CIでもuv.lockとの一致を確認
```

Python Functionの最大実行時間は300秒。`functions.excludeFiles`と`.vercelignore`でテスト・原本・作業記録・ローカル環境ファイル・frontendの資源をPython bundleから除外する。添付文書定義JSONなどbackendのruntime資源は保持する。

新しいPythonアプリはframework preset、Next.jsとの同居はServicesを使うのが公式案内の構成であるため、旧方式の`api/*.py`へコードを移動しない。Application/Domain/Infrastructureの配置と通常の`backend.main:app`起動を維持する。

## クラウド接続設定

バックエンドが使用する次の環境変数をVercelプロジェクトへ設定する。資格情報をGit、フロントエンドの`NEXT_PUBLIC_*`、ビルドログへ含めない。

```dotenv
MEDI_CHAT_DATABASE_HOSTS=ep-YOUR-ENDPOINT.YOUR-REGION.aws.neon.tech
MEDI_CHAT_DATABASE_URL=postgresql+psycopg://APP_ROLE:PASSWORD@ep-YOUR-ENDPOINT.YOUR-REGION.aws.neon.tech/DB_NAME?sslmode=require&channel_binding=require
PYTHON_DOTENV_DISABLED=1
AUTH_ISSUER=https://YOUR_APP_DOMAIN
AUTH_AUDIENCE=medi-chat
AUTH_KEY_ID=primary
AUTH_PRIVATE_KEY=SET_FASTAPI_ONLY_RSA_PRIVATE_PEM
AUTH_PUBLIC_KEYS=SET_JSON_MAPPING_KID_TO_PUBLIC_PEM
ALLOWED_ORIGINS=https://YOUR-FRONTEND.vercel.app
```

`VERCEL=1`の環境では、Vercelが設定する`VERCEL_URL`・`VERCEL_BRANCH_URL`・`VERCEL_PROJECT_PRODUCTION_URL`を許可Originへ追加する。PreviewごとのURLを手入力する必要はない。独自ドメインは`ALLOWED_ORIGINS`へ明示する。任意の`*.vercel.app`全体は許可しない。Servicesは環境変数を共有するため、秘密情報には`NEXT_PUBLIC_`を付けない。

Neonが発行する接続文字列のホストを許可リストへ明示する。TLSとchannel bindingを必須とし、URL内の`host`や`options`による接続先の上書きを拒否する。証明書検証方式を使う場合は`sslmode=verify-full&sslrootcert=system`も利用できる。ローカル接続と専用テストDBの既存の制限は維持する。

初回はNeonの直接接続先を使う。現在のengineは接続開始時の`options`でsearch_path・timeoutを設定するため、transaction pooling接続先についてはその設定・REPEATABLE READ・同時登録を実Neonで確認してから採用する。Functionインスタンスごとのpool上限は5接続、overflowなし。実際の同時インスタンス数に対するDB接続数はPreview検証で確認する。

DDL権限を持つ移行用roleと、runtimeのDML用roleを分ける。`pg_trgm`、schemaのUSAGE、既存・今後作成するテーブルへのSELECT/INSERT/UPDATE/DELETEを管理側で準備する。移行用資格情報はruntimeへ配置しない。マイグレーションはローカルの管理CLIから明示実行する。

```powershell
pnpm --filter backend db:migrate
```

このコマンドには`MEDI_CHAT_MIGRATION_DATABASE_URL`と、その接続先を含む`MEDI_CHAT_DATABASE_HOSTS`が必要。初回デプロイ前に同じCLIのinitializeで原本を登録する。空DBは現行のreadiness条件を満たさないため、起動後のWeb登録を初期化の代わりにしない。公開後の追加・更新はWeb画面から手動で行う。

## WebからのXML取り込み

- 最大10MiB。3MiB以下は既存のmultipart送信、超えるXMLは3MiB以下のraw binaryに分割する。各HTTP bodyをVercel Functionsの4.5MB制限未満に保つ。
- `POST /api/attachment-imports/uploads`にfilename・byte_size・source_sha256を送り、ランダムな256bitのupload_idを受け取る。このIDは一時セッションの操作用なので共有しない。
- `POST /api/attachment-imports/uploads/{upload_id}/parts/{index}`で0始まりの分割データを送信する。サーバーは位置・正確な部分サイズを検証。同一bytesの再送は成功し、異なるbytesでの置換は409とする。
- `POST /api/attachment-imports/uploads/{upload_id}/complete`で全体のサイズ・SHA-256を検証してから、既存のXML検証・改訂判定・atomicな公開処理へ渡す。欠落は409、全体のハッシュ不一致は422。既存と同じ登録結果DTO・Location、新規201／再送200を返す。
- 完了時に分割bytesを削除し、再試行に必要な小さいmetadataだけを保持する。同じ完了要求の再送は登録履歴の再送用結果を参照し、二重公開しない。原本payloadが旧版として削除済みでも200・reused=trueを返す。結果GETの削除済み判定（410）は維持する。公開後・セッション完了記録前に切断しても、既存publisherの原本ハッシュによる冪等性を使って再試行できる。
- 有効期間は作成から最大1時間。未完了セッションは最大16件（原本bytesは最大160MiB）。完了metadataは作成時に直近64件へ整理する。期限切れセッションとその部分データは次のセッション作成、または`pnpm --filter backend db:maintenance`で回収する。TTL到達時に常駐タイマーで削除する構成ではない。
- 送信失敗時は画面にサーバーのエラーを表示し、手動で再送できる。ページ再読込後の途中再開や、自動のXML再登録は行わない。
- XML・メタデータ・全体ハッシュの不正、上限超過、改訂競合など確定的な取り込み失敗では、セッションと部分bytesを削除して取り込み枠を解放する。未送信部分がある409と一時的な保存障害・取消では再試行用に保持する。

## デプロイ時に残る作業

公開前に[個人ログイン](authentication.md)の鍵設定・アカウント準備とPreview検証を完了する。認証の設定不足ではFastAPIは起動しない。Next.jsへ秘密鍵を渡さない。

1. Vercel MarketplaceでNeonを作成し、ProductionとPreviewのDBを分離する。
2. GitリポジトリをRoot Directory `.`でImportする。ルートのServices設定を使い、DB接続情報・独自ドメインのOriginを設定する。
3. APIキーをバックエンドの環境変数へ設定。Functionの実行時間・メモリ・Fluid computeと公開範囲を設定する。
4. 実Neonでmigration・初期登録後、Previewで10MiBアップロード、インスタンスをまたぐ再送、検索、WebSocket切断・再接続、接続数と時間を検証する。

クラウド資源作成・実Neon接続・Vercelビルド／デプロイはローカルテストでは検証できない。実施結果と分けて扱う。

## 公式資料

- [Vercel PostgresとMarketplace](https://vercel.com/docs/postgres)
- [Vercel Functionsのbody制限](https://vercel.com/docs/errors/function_payload_too_large)
- [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi)
- [WebSockets](https://vercel.com/docs/functions/websockets)
- [Neonの接続文字列](https://neon.com/docs/reference/cli-connection-string)
- [Python runtime](https://vercel.com/docs/functions/runtimes/python)
- [Python Functions in /api](https://vercel.com/docs/functions/runtimes/python/api-directory)
- [Python version](https://vercel.com/docs/functions/runtimes/python/python-version)
- [Services](https://vercel.com/docs/services)
- [Servicesの設定](https://vercel.com/docs/services/config-reference)
