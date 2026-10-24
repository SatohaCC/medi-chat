# 個人ログインの設定と運用

認証窓口はFastAPIに集約する。Next.jsからAPIへの中継は追加せず、Vercel Servicesの同一オリジン経路を維持する。秘密URL方式は廃止し、旧Cookie・APP_SECRET_KEYでは通過できない。

## 初回の準備

リポジトリルートで実行する。以下は管理者が環境ごとに明示実行する手順であり、起動時の自動変更ではない。

```powershell
uv sync --project backend --locked
uv run --project backend python -m backend.infrastructure.cli.authentication generate-keys
```

3072bitのRSA秘密鍵と公開鍵JSONを`.auth/`へ生成する。既存鍵は上書きしない。このフォルダはGit管理外で、環境ごとに管理する。秘密鍵をコミット、共有ログ、Next.jsの環境、NEXT_PUBLIC変数へ置かない。

FastAPIの環境には`.env.example`のAUTH変数を設定する。ローカルPowerShellでは、例えば次のように生成ファイルを現在の起動プロセスへ読み込める。

```powershell
$env:AUTH_ISSUER = 'http://localhost:8000'
$env:AUTH_AUDIENCE = 'medi-chat'
$env:AUTH_KEY_ID = 'primary'
$env:AUTH_PRIVATE_KEY_FILE = '.auth/private.pem'
$env:AUTH_PUBLIC_KEYS = Get-Content -LiteralPath .auth/public-keys.json -Raw
```

ローカルではルート`.env.local`にAUTH_PRIVATE_KEY_FILEの相対パスを設定し、秘密PEM本体をNext.jsへ読み込ませない。本番ではFastAPI専用のAUTH_PRIVATE_KEYへPEMを設定し、AUTH_PRIVATE_KEY_FILEは設定しない。同時指定は拒否する。秘密PEMの改行は実改行またはリテラルの`\n`を使える。公開鍵JSON内の改行はJSONのエスケープを使う。issuerは環境固有の信頼する発行者、audienceはmedi-chat API向けの固定値にする。

既存PostgreSQLへ現行マイグレーションを適用し、アカウントを作成する。

```powershell
pnpm db:migrate
uv run --project backend python -m backend.infrastructure.cli.authentication create
```

createはログインIDとパスワードを対話入力する。パスワードは15〜128文字で、引数やログへ表示しない。作成にruntime用DBのDML権限が必要で、DDL権限は不要。ログインIDは前後空白だけを除去し、大文字小文字を区別する。公開サインアップ・招待・メール再発行画面は提供しない。

## 通信と期限

- `/api/auth/login`、`refresh`、`logout`、`me`を使用する。トークンはJSONへ出さず、HttpOnly Cookieだけへ保存する。
- アクセスJWTは30分。更新系列はログインから7日の絶対期限。更新しても7日を延長せず、直前のJWTもこの期限を超えない。
- 通常APIは署名・用途・発行者・宛先・期限をローカル検証し、認証用DBを照会しない。業務データのDB照会は別である。
- アクセスCookieはPath=/、更新CookieはPath=/api/auth。Domain指定なし、SameSite=Lax。非ローカルDB利用時とVercelではSecure必須。ローカルHTTP用設定のまま外部公開しない。
- 更新系HTTPは許可Originと`X-Medi-Chat-CSRF: 1`が必要。WebSocketも許可Originが必要。独自ドメインや開発ポートは`ALLOWED_ORIGINS`へ明示する。資格情報付きCORSで`*`は使用しない。
- WSはaccept前と接続中の期限を検証する。期限で生成を中断し、4001で閉じる。ブラウザは更新後に再接続するが、質問・インポートを勝手に再送しない。
- 複数タブはWeb Locksで更新を直列化する。非対応ブラウザでは期限切れ時に再ログインする。更新応答を失った場合も同じ更新値を自動再送しない。
- `/health`と`/api`も認証対象。configured smokeは設定済み鍵で短命の試験用JWTを生成し、read-onlyのhealthだけを要求する。公開healthは新設しない。

## 停止・再設定・削除

```powershell
uv run --project backend python -m backend.infrastructure.cli.authentication stop
uv run --project backend python -m backend.infrastructure.cli.authentication reset-password
uv run --project backend python -m backend.infrastructure.cli.authentication cleanup
```

停止とパスワード再設定は対象利用者の更新セッションを失効させる。再設定だけで停止アカウントは再開しない。ログアウトは現在の更新系列だけを失効させる。DB障害時は503で失効失敗を返す。

発行済みのアクセスJWTは、コピーされたものも含め最大30分有効なままである。即時失効が必要になった場合は認証DB照会または短期キャッシュ等の設計変更が必要になる。

cleanupは絶対期限を過ぎた更新系列と古いログイン試行窓を削除する。再利用検出に必要な使用済みトークンは系列の絶対期限まで保持する。自動スケジュールは今回作成しない。

## 負荷と設定

共有PostgreSQLでログインID・接続元ごとの試行窓を管理する。既定は900秒あたりID10回・接続元60回で、AUTH_LOGIN_LIMIT、AUTH_ADDRESS_LIMIT、AUTH_LOGIN_WINDOW_SECONDSで設定できる。成功も予算に数える。AUTH_HASH_PARALLELISMはプロセス内のArgon2id同時実行数（既定2）。複数インスタンス全体のCPU制限を保証する値ではない。

接続元はASGIのclient情報を使い、アプリから任意のX-Forwarded-Forを読まない。Uvicorn/プラットフォームが信頼するプロキシの設定を配置環境で限定する。誤設定では接続元の集約・偽装が起きるため、Previewで確認する。

## 鍵の切り替えと認証基盤の交換

AUTH_PUBLIC_KEYSはkidから公開鍵PEMへのJSON対応表。新しい秘密鍵・kidを有効にする際に旧公開鍵も保持し、最後の旧鍵発行から30分以上経過してから除去する。環境間で鍵を使い回さない。未知kidやトークン指定の鍵URLは採用しない。

アプリの所有者IDはUserId。auth_identitiesで`(issuer, subject)`と対応させ、メール一致だけで自動リンクしない。将来のOIDC接続・本人確認を伴う対応付け・トークン交換は別の移行作業である。JWT採用だけで任意の外部基盤へ無変更で移行できるとは扱わない。

## 検証の区別

DB不要のbackend試験、実暗号ライブラリ、Nodeの更新調整、APIモック付きChromium、実PostgreSQL契約を分けて実施・報告する。実PostgreSQLは既存CIの`pnpm test:postgres`で実施する。Vercel Preview・実OIDC・外部LLMの通信成功をローカル試験から推定しない。
