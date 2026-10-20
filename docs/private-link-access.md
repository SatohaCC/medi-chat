# 秘密URLによるアクセス制限（Issue #29）

## 配布と設定

Vercelプロジェクトにserver-onlyの`APP_SECRET_KEY`を設定する。Next.jsとFastAPIには同じ値を渡す。`NEXT_PUBLIC_`を付けない。Vercelではキー未設定・32bytes未満の設定を拒否するため、保護なしで起動しない。プラットフォーム判定だけに依存せず、Next.js本番モードと、非ローカルDBを使うFastAPIでもキーを必須にする。

十分長いランダム値を生成し、Vercelの環境変数へ保存する。生成値をGit・Issue・PR本文へ含めない。

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

対象者には`https://<domain>/?key=<APP_SECRET_KEY>`を配布する。画面URLへのGETで正しいキーが渡された場合のみCookieを発行し、303で`key`を除いたURLへ戻す。パスと他のクエリは維持する。APIやWebSocketにクエリキーを直接付けても認証されない。

## Cookieと検証

- Cookie名は`medi_chat_access`。秘密キーやその固定ハッシュではなく、版・期限・ランダムnonceにHMAC-SHA256署名を付けた値を使用する。Next.jsで発行し、Next.jsとFastAPIの両方で検証する。
- 有効期間30日、HttpOnly、SameSite=Lax、Path=/、Domain指定なし。本番・Vercel・HTTPSではSecureを付ける。
- 期限切れ・改ざん・異なるキーで署名されたCookieは拒否する。APP_SECRET_KEYを変更して再デプロイすれば、新デプロイでは既存Cookieが無効になる。共有リンクも新しいものへ変更する。
- 認証関連レスポンスは`Cache-Control: private, no-store`と`Vary: Cookie`を設定。専用URLからのリダイレクトには`Referrer-Policy: no-referrer`も設定する。

## 保護する場所

Next.js 16では`middleware.ts`ではなく`frontend/proxy.ts`を使う。未認証の画面は403で制限メッセージを表示し、APIは401を返す。`_next/static`・`_next/image`・faviconをmatcherから除外する。キー設定自体が不正なホスティング環境では503とし、通過させない。

Servicesの`/api/*`・`/health`・`/ws/chat`はNext.jsを通らずFastAPIへ届く。このためFastAPIにもASGI middlewareを置き、全HTTP/WS要求をRouter・Depends・LLM処理より前に検証する。未認証HTTPは401、WebSocketはaccept前に拒否（1008）。UIだけの遮断には依存しない。

CORSの許可されたpreflightはCookieなしで処理できるが、実際のAPI要求には有効なCookieが必要。API fetchはCookieを含め、ローカルのfrontend/backendのportが異なる場合にも対応する。

## ローカルと公開前検証

ローカルはキー未設定なら従来どおり動く。認証を確認する場合は、ルートの`.env.local`に`APP_SECRET_KEY`を設定する。Next.js・FastAPI・DB管理CLIで共有する。既存のプロセス環境変数が優先されるため、古い値があれば起動元から除いて再起動する。Vercel上では同一プロジェクトの環境変数を使用する。

```powershell
pnpm --filter frontend test:e2e:access
```

この試験は専用の偽キーを持つNext.js/Chromiumを使い、403/401・秘密URL交換・HttpOnly・期限切れ・改ざん・Secure属性・設定不足の拒否を確認する。FastAPIの境界試験と実DB付きアプリ試験はbackend側で行う。外部LLMの実通信は不要。

公開前には実Vercel Previewでも、秘密URLからの利用・URLからのkey除去・Cookie・REST・WebSocket・未認証のAPI直接呼出しを確認する。APP_SECRET_KEYの実環境設定とクラウド上の検証は、ローカル試験と区別する。
