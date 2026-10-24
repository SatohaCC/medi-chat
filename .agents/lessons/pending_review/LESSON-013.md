# LESSON-013: 必須認証設定の導入時は通常開発設定で実起動を確認する

- 状態: pending_review
- 作成日: 2026-10-24
- 最終確認日: 2026-10-24
- 承認者・承認日・承認の参照: 未承認
- 更新案の場合の対象: なし
- 統合先・廃止理由: なし

## 本文を読むトリガー条件

起動時に必須となる認証設定・署名鍵・DBスキーマを追加する変更。テスト鍵では成功するが通常のpnpm devが設定不足で停止した場合。

## 適用する条件／適用しない条件

通常dotenvを使う開発起動の契約を変更するときに適用する。テスト鍵を本番へ配置する提案、認証なしのフォールバック、無許可の本番DB変更には適用しない。

## 観察した失敗と証拠

認証の境界試験・APIモック付きブラウザ試験後、ユーザーの通常起動で`Authentication configuration is missing or invalid`が発生した。署名鍵を含むAUTH変数が未設定であり、開発DBも追加前のrevisionだった。

本体の参照箇所は`backend/config/authentication_settings.py`、`backend/infrastructure/composition/app_lifespan.py`。修正後は`backend.infrastructure.cli.configured_e2e_gate`で通常dotenv・実OS・認証付きread-only healthが終了コード0となった。秘密情報と機械固有パスは記録しない。PR・コミットは未作成。

## 原因

テスト用環境と通常開発設定が異なる。必須設定を導入しても、テスト鍵だけを使う検証では実開発設定の不足を検出できなかった。設定不足で拒否する認証方針自体は維持した。

## 次回の具体的な確認手順

1. 必須設定と必要なDB revisionを計画に明示する。
2. 通常設定では秘密値を表示せず、必須キーの有無、接続先の所有とrevisionを確認する。
3. 鍵とDBの変更は環境の所有・許可を確認する。資格情報の取得・保存が自動レビューで拒否された場合は、理由を伝えて明示許可を求める。
4. 専用portのconfigured gateで通常dotenvを保持し、実サーバー起動と認証付きhealthを確認する。試験所有プロセスのみを終了する。

## 対策の検証

- ローカル開発鍵の設定と、認証テーブル6件の追加後に実起動・health成功を確認した。
- 原本と既存業務データは削除していない。ログインアカウントは自動作成していない。
- 本番Vercel・外部OIDC・全PostgreSQL契約試験はこの起動確認の成功に含めない。
- 既存の`docs/development/validation.md`とconfigured gateを使用する。新たな承認済み規約やINDEX登録はしていない。

## 次の関連作業での評価

PR #69初回CIで、実PostgreSQL試験の既存APIクライアントとOS health probeに認証利用者の設定漏れが6件あった。認証導入時の確認対象には、通常開発起動だけでなく、CI専用のHTTP・WebSocket・OSプロセス経路も含める提案を追記する。署名Cookie・Origin・CSRFを明示する共通ヘッダーを追加し、試験から本番の認証境界を通す。ローカルのDB不要成功を実DB成功として扱わず、再実行CIで確認する。承認待ち。
