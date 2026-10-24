# 個人認証の実装計画

状態: 2026-10-24にユーザーが実装計画・別紙テスト仕様をそれぞれ承認。ローカル実装・検証を実施。[検証記録](authentication-validation.md)に成功範囲・既存失敗・未実施事項を記載。

## 合意した方針

- 初期はアプリ内のID・パスワード認証。将来、外部OIDC基盤へ差し替えられる境界を設ける。
- FastAPIへ認証窓口を集約する。Next.jsに全APIを中継するBFFは追加しない。
- アクセストークンはJWT、有効期限30分。リフレッシュトークンはランダム値、有効期限7日。
- アプリ内のUserIdと認証基盤のユーザー識別子を分離する。
- 通常の保護APIはJWTのローカル検証で認証し、認証のためのDB照会を行わない。
- 失効後も発行済みJWTは最大30分利用できる。WebSocketについても期限を適用する。

## 今回承認する追加仕様案

- 7日はログイン時からの絶対期限とする。ローテーションしても延長せず、JWTの期限もこの絶対期限を超えない。
- 既存の秘密リンク認証を置き換える。旧Cookie・URLキー・APP_SECRET_KEYによる通過は残さない。
- 初期アカウントの作成、パスワード再設定、利用停止は管理CLIで行う。秘密値は対話入力し、引数・ログへ出さない。公開サインアップやメール送信は今回含めない。
- ログインIDはメールアドレスを必須としない。前後空白を除去し、大文字小文字を区別して一意にする。パスワードは正規化・切り詰めを行わず、15〜128文字を受け付ける。
- 所属・ロール管理の画面、権限体系の新設、チャット履歴の保存方式変更は含めない。初期は有効な利用者に既存機能の利用を許可する。

## 現状と変更点

`vercel.json`は画面をNext.js、`/api/*`と`/ws/chat`をFastAPIへ直接振り分ける。この経路を維持する。現在の`frontend/proxy.ts`と`backend/presentation/access_control.py`は、個人識別のない秘密リンクCookieを検証している。

| 対象 | 変更する責務 |
| --- | --- |
| `backend/domain/identity/`（新規） | UserId、ログインID等のPrimitive、利用者の有効・停止状態、外部識別子との対応、不変条件 |
| `backend/application/authentication/`（新規） | ログイン、更新、ログアウト、利用者確認、管理CLIの操作をユースケース別に配置。認証プロバイダー、時計、トークン処理、永続化等はinterfacesへ置く |
| `backend/infrastructure/authentication/`（新規） | ローカル資格情報の照合、パスワードハッシュ、JWT発行・検証、乱数生成。外部OIDC実装の将来の差し替え先 |
| `backend/infrastructure/persistence/`・`backend/migrations/` | 利用者、外部識別子の対応、ローカル資格情報、更新セッション、使用済み更新トークン、試行制限の永続化 |
| `backend/presentation/` | 認証API・DTO・HTTP/WSガード。内部には検証済みの利用者情報だけを渡す |
| `backend/config/`・`backend/infrastructure/composition/app_lifespan.py` | 型付き設定の検証、アダプター生成、注入、終了処理。秘密値を表示しない |
| `backend/main.py` | 新ガードと認証ルートを配線。ログイン等の公開ルートは明示的に限定 |
| `backend/application-architecture.toml`・依存検査 | 新Featureの依存・公開契約を登録。既存の例外ゼロのレイヤー境界を維持 |
| `frontend/app/login/`・`frontend/features/authentication/`（新規） | ログイン画面、現在の利用者、更新調整、ログアウト。プロバイダーSDKやJWTの解釈を画面へ持ち込まない |
| `frontend/shared/api/`・チャット接続処理 | Cookie送信、認証期限切れの区別、更新後の再接続。処理済み操作やLLM生成を自動再送しない |
| `frontend/proxy.ts`・`frontend/shared/server/accessToken.ts` | 秘密キー交換・独自署名処理を廃止。画面ガードは表示補助とし、FastAPIで必ず認証する |
| 管理CLI・設定例・開発/デプロイ手順 | アカウント準備、鍵の準備と切り替え、DB更新、ローカル起動、旧方式廃止を記載 |

Applicationは既存のcommands/queries/interfaces構成に従う。PresentationからDomain・Infrastructureへの直接依存、Domain/ApplicationへのPydantic・暗号ライブラリ依存を追加しない。不要な空ファイルや互換Facadeは作らない。

## 認証基盤を差し替える境界

外部識別子は`(issuer, subject)`で一意に管理し、アプリのUserIdへ対応付ける。ローカル認証にも独立した識別子を割り当てる。メールアドレス一致による自動リンクは行わない。

認証アダプターは、検証した外部識別子・期限等をApplicationの型へ変換する。業務処理はプロバイダーのJWT claimやSDK型を参照しない。通常APIに毎回の対応表照会が必要にならないよう、初期JWTには発行時に確定したUserIdを含める。

将来のOIDC接続、既存アカウントの本人確認を伴う対応付け、外部JWTを直接受けるかアプリ用セッションへ交換するかは移行時に設計する。今回の自作ログインをOIDCサーバーとして実装することは含めない。移行後もDB照会ゼロ・同じ期限を無条件に保証しない。

## API契約案

| API | 成功時 | 主な失敗 |
| --- | --- | --- |
| `POST /api/auth/login` | ID・パスワード照合後にCookie設定、利用者と期限を返す | 不一致・停止は共通の401、試行制限429、基盤障害503 |
| `POST /api/auth/refresh` | 更新トークンを原子的に交換し、Cookieと期限を更新 | 期限切れ・失効・再利用は401、基盤障害503 |
| `POST /api/auth/logout` | 現在の更新セッションを失効しCookie削除、204 | DB失敗は503とし、失効成功と報告しない |
| `GET /api/auth/me` | JWT内の検証済みUserIdと期限を返す。認証用DB照会なし | 未認証・期限切れ401 |

JWTと更新トークンはJSONへ出さない。認証応答は`private, no-store`。401は`access_expired`と他の認証失敗を区別し、403や503で自動更新を繰り返さない。更新・ログアウトはアクセストークンの有効期限に依存せず、更新CookieとCSRF検証で処理できるようにする。

## トークン・Cookie・防御

- JWTは既存の標準ライブラリ実装を利用する。固定した非対称署名方式、kid、iss、aud、sub、iat、exp、用途を検証し、任意のalgや鍵URLを受け入れない。アプリ用subはUserIdとする。
- 秘密鍵はFastAPIのみが保持する。検証鍵の識別とローテーション手順を用意し、未知のkidを拒否する。外部JWKSの取得は今回実装しない。
- 更新トークンの平文はCookieのみへ返す。DBにはハッシュとセッション系列・期限・失効・使用履歴を保持する。
- 交換はDBトランザクション内で原子的に行う。使用済みトークンの再利用で系列を失効させる。保存期間は系列の絶対期限までとし、削除CLIを用意する。
- アクセスCookieはHTTP/WSの両経路に届くPath=/。更新CookieはPath=/api/auth。Domain属性なし、HttpOnly、SameSite=Lax、本番Secure。旧Cookieと異なる名前を使う。
- 更新系HTTP（ログインを含む）は許可Origin検証とカスタムヘッダーによるCSRF対策を行う。Origin欠落時も通過させず、開発時の許可Originを明示する。WebSocketもOriginを検証する。
- パスワードはArgon2id。ハッシュ計算をイベントループ外で、同時実行数を制限して行う。未知IDでもダミーハッシュ照合を行い、利用者の存在を応答で区別しない。
- ログイン試行制限はプロセスローカルだけに依存させない。共有PostgreSQLで正規化IDと信頼できる接続元単位の窓を管理し、上限超過はハッシュ計算前に拒否する。信頼するプロキシ情報を明示し、任意の転送ヘッダーを信用しない。制限値とハッシュ並列数は設定・試験対象にする。
- パスワード・Cookie・トークン・秘密鍵をログへ出さない。通常APIに失効DB確認を追加しないため、停止・再設定・ログアウト後のJWT利用は最大30分残る。

## ブラウザ・WebSocket

- localStorageへトークンを保存しない。画面起動時にmeを確認し、必要なら更新を1回行う。安全な同一オリジン内のreturnToのみを許可する。
- 同一タブはsingle-flight、複数タブも更新用ロックで直列化する。ロック取得後にmeを再確認し、先行更新済みならrefreshを呼ばない。Web Locks非対応環境では自動更新を行わず、明示的な再ログインへ戻す。
- 更新失敗時は接続を停止して再ログインへ誘導し、無限ループを作らない。ネットワーク断後の更新の自動再送も行わない。
- WebSocketはaccept前に認証し、接続後もexpで閉じて実行中の生成をキャンセルする。1メッセージごとの認証DB照会は行わない。
- 期限切れ後はHTTPで更新して再接続する。送信済み質問・インポート・生成の自動再実行は行わず、途中まで表示した回答の扱いを画面で明示する。
- ログアウトは当該ブラウザの他タブにも通知し、接続・利用者表示を解除する。コピー済みJWTや別クライアントへの即時失効を保証しない。

## 実施順

1. この計画を承認後、別紙テスト仕様を承認する。
2. 認証境界・時計・保存契約と意味のある失敗ケースからテストを作り、Domain/Applicationを実装する。
3. PostgreSQLの保存・原子的交換と暗号アダプターを追加する。依存はロックファイルを正規更新する。
4. HTTP/WSガードと管理CLIを配線し、秘密リンク方式を削除する。
5. ログイン画面・更新調整・ログアウト・WS再接続を実装する。実装前に同梱Next.jsガイドと対象UIスキルを確認する。
6. 別紙の層別検証と負荷測定を行い、実測・未実施を区別して報告する。

認証の設定不足で保護なしに起動するフォールバックは設けない。試験は明示的なテスト鍵・アカウント・保存アダプターを使用する。最小healthを公開する必要性と既存health契約は実装時に照合し、認証以外の内部情報を公開しない。

本番DB変更、実アカウント作成、Vercel設定、公開、pushはこの計画作成に含まない。

## 参考

- [OIDC Core: issuerとsubject](https://openid.net/specs/openid-connect-core-1_0.html)
- [RFC 9068: JWTアクセストークンの検証](https://www.rfc-editor.org/rfc/rfc9068.html)
- [RFC 9700: 更新トークンの再利用検出](https://www.rfc-editor.org/rfc/rfc9700.html)
- [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
