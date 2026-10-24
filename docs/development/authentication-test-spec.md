# 個人認証のテスト仕様

状態: 2026-10-24にユーザーが承認。[実装計画](authentication-plan.md)に対応。実施結果は[検証記録](authentication-validation.md)を参照。実PostgreSQL契約と本番環境は未実施。

## 受入ケース

| ID | 入力・状況 | 観測する期待結果 | 層 |
| --- | --- | --- | --- |
| AUTH-01 | 有効なID・パスワード | 利用者を識別し、アクセス期限が30分、更新系列期限がログインから7日になる | Application・HTTP |
| AUTH-02 | 誤パスワード、未知ID、停止利用者 | 同じ形式の401。秘密値・存在有無を応答とログへ漏らさない | Application・HTTP |
| AUTH-03 | 期限境界、改ざん、異なる署名・iss・aud・用途、未知kid、禁止alg | 有効なものだけ通過。期限ちょうどで拒否し、業務・LLM処理を呼ばない | 暗号adapter・HTTP/WS |
| AUTH-04 | 通常の保護API・meを反復 | JWT検証は行うが、認証Repository・更新保存・外部HTTPを呼ばない | Application・HTTP |
| AUTH-05 | 有効な更新トークン | 旧値を使用済みにし、新Cookieを返す。DB平文保存なし、期限を7日から延長しない | Application・PostgreSQL |
| AUTH-06 | 7日直前の更新、7日ちょうどの更新 | JWTも絶対期限を超えない。7日ちょうどで更新拒否 | Application |
| AUTH-07 | 期限切れ、失効済み、存在しない更新値 | 401、新しい系列を発行しない | Application・HTTP |
| AUTH-08 | 使用済み更新値の再利用 | 系列全体を失効。直前に発行した更新値も拒否。既発行JWTの期限までは独立して有効 | Application・PostgreSQL |
| AUTH-09 | 同じ更新値を同時に2要求、交換途中のDB失敗 | 交換の成功は最大1件。再利用は系列失効。失敗途中の部分更新・トークン発行成功なし | 実PostgreSQL |
| AUTH-10 | ログアウト、停止、パスワード再設定 | 対象の更新セッションを失効。コピー済みアクセスJWTは期限までの許容範囲でのみ有効 | Application・PostgreSQL |
| AUTH-11 | DB停止中の更新・ログアウト | 503。ログアウト失効成功を偽装しない。通常JWTの認証判定はDBを呼ばない（業務DB障害は別） | HTTP・adapter |
| AUTH-12 | 本番Cookieと応答を確認 | HttpOnly/Secure/SameSite/Path/Domainなし、no-store。トークンがJSON・URL・localStorageにない | HTTP・ブラウザ |
| AUTH-13 | 不許可・欠落Origin、不正CSRFヘッダー、許可preflight | 更新系HTTP・WSを拒否。preflight成功で実APIの認証を省略しない | HTTP/WS・ブラウザ |
| AUTH-14 | 規定回数のログイン失敗、別インスタンスからの続行 | 共有の制限が働き429。超過後のハッシュ計算なし。転送ヘッダー偽装で回避不可 | Application・PostgreSQL・HTTP |
| AUTH-15 | ハッシュ処理を同時実行 | 同時実行上限を守る。イベントループをブロックせず、平文・ハッシュを応答へ出さない | adapter |
| AUTH-16 | UserIdが同じで外部識別子が変更、同じメールで別subject | 前者はアプリ所有者IDを維持。後者は自動リンクしない | Domain・Application・PostgreSQL |
| AUTH-17 | 認証プロバイダーのテスト実装へ差し替え | Presentation・業務ユースケース変更なしで同じ利用者契約を満たす。実OIDC成功とは報告しない | Application・composition |
| AUTH-18 | UI未認証、リロード、同一サイトreturnTo、外部URL指定 | ログイン・復帰が成立。外部リダイレクトを拒否 | ブラウザ |
| AUTH-19 | 多数の同時APIと2タブで期限切れ | 更新が直列化され、先行更新後のタブは不要な再交換なし。正常利用で系列失効しない | frontend単体・複数タブ実ブラウザ |
| AUTH-20 | 更新401/503、ネットワーク応答喪失、Web Locks非対応 | 無限更新・盲目的再送なし。再ログインへ誘導し、元の更新操作を勝手に再実行しない | frontend単体・ブラウザ |
| AUTH-21 | WS未認証・期限切れ接続 | accept前に拒否しLLMを呼ばない | WS |
| AUTH-22 | WS待機中・生成途中でJWTが期限切れ | 期限で切断・生成キャンセル。HTTP更新後は再接続でき、元質問の二重送信なし | WS・ブラウザ |
| AUTH-23 | 一方のタブでログアウト | 他タブの利用者表示・WSを解除。別クライアントの即時失効は期待しない | 複数タブ実ブラウザ |
| AUTH-24 | 旧秘密URL・旧Cookie、署名鍵等の未設定 | 認証通過なし。本番は設定不足でfail closed。公開範囲は明示したルートのみ | 起動・HTTP・ブラウザ |
| AUTH-25 | 管理CLIで作成・重複・停止・再設定 | 対話入力し秘密値を表示しない。一意制約と状態変化が働き、別利用者へ影響なし | Application・CLI・PostgreSQL |
| AUTH-26 | 検証鍵切り替え、旧鍵の許容期間終了 | 許可した旧新kidのみ検証。期限終了した旧鍵・任意鍵URLは拒否 | 暗号adapter・設定 |
| AUTH-27 | 期限切れ系列の削除 | 期限内のセッションと再利用検出情報を保持し、期限切れだけを削除 | PostgreSQL・CLI |
| AUTH-28 | 未認証で検索・chat・import・upload・各WS aliasへ直接アクセス | 全経路で業務開始前に拒否。ルート追加が保護から漏れない | HTTP/WS・architecture |
| AUTH-29 | 新しい境界から禁止レイヤーを参照する合成コード | ハーネスが違反を検出。実装側は例外追加なしで通る | architecture |

## 検証の分離と実行順

1. 変更前の対象範囲を確認し、既存失敗と今回の失敗を区別する。時間・依存障害がある結果を正常baselineとしない。
2. ローカルは時計・乱数・保存アダプターを制御したDB不要のDomain/Application/HTTP/WS試験、実暗号ライブラリ試験を行う。暗号の安全性そのものをテストで証明したとは報告しない。
3. 実PostgreSQLは既存CIの`pnpm test:postgres`で、空schemaへのマイグレーション、原子的交換・競合・一意制約・rollbackを検証する。SQLiteに置き換えない。接続設定不足をskipで成功扱いしない。
4. frontend単体と実ブラウザを分ける。APIモックによる画面試験と、実FastAPI・専用試験PostgreSQLによるCookie/認証/WS試験を分けて報告する。テストデータの表示名は「テスト利用者」。外部LLMはダブルでよく、実通信成功とは扱わない。
5. `pnpm quality:changed --list`で選択コマンドを確認して対象品質検査を実行する。backend lint・Domain/Applicationハーネス・型・frontend lint/型/ビルドと、変更に必要な回帰を確認する。
6. Vercel PreviewのSecure Cookie・同一オリジンrouting・WSは公開承認後の別検証とする。ローカル成功を本番成功とは報告しない。

## 負荷の確認

- 通常APIの認証DB照会0回をspyで検証し、実環境試験でも認証クエリを識別して観測する。API全体のDB照会0回とはしない。
- ローカル固定環境で署名検証だけのコスト、ログインのハッシュ計算、更新トランザクションを分けて測る。単独と同時実行のサンプル数、並列数、CPU/メモリ、p50/p95、エラー率を記録する。
- WebSocketはメッセージごとの認証DB照会なしを検証し、期限タイマー・切断後のタスク解放も観測する。
- JWT検証の結果をプロセスごとにセッションキャッシュする方式やRedisは、必要性が実測されるまでは導入しない。
- 同時利用者数・目標RPS・許容p95は未指定。測定結果から処理可能人数や本番SLO達成を推測して断言しない。

実行コマンド・終了コード・件数・対象差分を記録し、未実施・skip/xfail・環境不足を独立して報告する。
