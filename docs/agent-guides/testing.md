# テスト設計と実装

- backendは`backend/tests/`、データツールは`data_tools/tests/`と各pyprojectのpytest設定を確認する。frontendには`frontend/app/lib/chatWebSocket.test.mjs`のNodeテストがある。追加時は対象範囲の既存配置・実行方法に合わせる。
- 期待結果は要件と公開契約から導き、実装の判定式をコピーしない。対象モデルは実オブジェクトを使い、外部SDK・通信などには適切な既存ダブルを使う。
- テストダブルの成功を実通信・実DB・ブラウザの成功と扱わない。必要な検証層・環境条件を仕様に示す。
- feature-pipelineでは承認済みケースと実テストの対応を保持する。Fixture/Fakeでも入力条件・観測・期待結果が変わる場合は仕様変更として戻す。
- カタログやXML変換の変更では[package_inserts/README](../../package_inserts/README.md)と対象テストを確認し、原本情報の保持を観測する。
- 実行方法と自動修正を避ける方法は[validation](validation.md)の該当節を使う。
