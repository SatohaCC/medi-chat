# テスト設計と実装

- backendは`backend/tests/`（移行済みXML/辞書CLIテストを含む）とbackend/pyprojectのpytest設定を確認する。frontendには`frontend/features/chat/api/chatWebSocket.test.mjs`のNodeテストがある。追加時は対象範囲の既存配置・実行方法に合わせる。
- 期待結果は要件と公開契約から導き、実装の判定式をコピーしない。対象モデルは実オブジェクトを使い、外部SDK・通信などには適切な既存ダブルを使う。
- テストダブルの成功を実通信・実DB・ブラウザの成功と扱わない。必要な検証層・環境条件を仕様に示す。
- feature-pipelineでは承認済みケースと実テストの対応を保持する。Fixture/Fakeでも入力条件・観測・期待結果が変わる場合は仕様変更として戻す。
- カタログやXML変換の変更では[Infrastructure定義README](../../backend/infrastructure/package_insert_definitions/README.md)と対象テストを確認し、原本情報の保持を観測する。
- 実行方法と自動修正を避ける方法は[validation](validation.md)の該当節を使う。
- 通常E2Eのconfigured起動確認（通常dotenv、実OSのhealthのみ）と、copy suite（keys空/dotenv無効、実browser保存）を分ける。旧manifest起動回帰ではfresh builderでstaleを消さず、旧索引整合copyの拒否→明示CLI→同一copyの回復を観測する。processは専用portを先に確認し、試験所有だけを終了する。
