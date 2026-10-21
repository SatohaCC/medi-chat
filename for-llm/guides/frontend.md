# フロントエンド

- [frontend/AGENTS.md](../../frontend/AGENTS.md)のNext.js案内を確認し、実装前にインストール済みNext.jsの対象ガイドを読む。生成される案内ブロックを削除・複製しない。
- 依存・スクリプトは[frontend/package.json](../../frontend/package.json)、型・lint設定は対象パッケージの設定を正典にする。
- useEffectは接続や購読など外部システムとの同期に使い、ユーザー操作やメッセージ処理はイベント・コールバックに置く。
- チャットの変更ではREST/WebSocketの契約、切断・再接続、進行中の回答と次の送信履歴への影響を対象範囲に応じて確認する。
- 型・lint・ビルド、接続ヘルパーの単体テスト、ブラウザと実サーバー接続の検証を区別する。コマンドは[validation](validation.md)のfrontend節を参照する。
