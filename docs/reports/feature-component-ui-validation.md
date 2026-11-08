# feature → component → ui の移行検証

## 変更した境界

既存の作業ツリーを基準に、featureからshared/uiへの直接参照を取り除いた。既存の未コミット差分を取り消さず、UIライブラリの直接importはshared/uiとProviderが所有する。componentはshared/uiを利用して表示とAPI変換を担う。

| featureに残す責務 | componentに分離した責務 |
|---|---|
| ログイン・ログアウト・登録・検索の処理と状態 | ActionButton、Form、TextInput、SearchInput、SwitchControl、FilePicker、Noticeによる操作・値・エラーの表示契約 |
| モデル選択肢・接続状態の判定 | SelectFieldの文字列選択値とStatusIndicatorの表示 |
| 薬剤候補の検索・選択済み薬剤・YJコードの判断 | SearchablePickerのポップアップ・フォーカス・ネイティブ選択APIとRemovableTagsの削除操作 |
| 薬剤補完データ、送信内容、未送信質問の保存・復元 | TokenPromptInputのContext・補完メニュー・カーソル・入力UI、ライブラリ非依存のPromptDocument |
| 評価API、楽観的更新、失敗・再試行 | RatingControlの選択値変換、ツールチップ、アイコン、既存アニメーション |
| 根拠の絞り込み、生成状態の判定 | ChoiceChipとLoadingIndicatorの表示契約 |

Buttonの実装・スタイル・既存Storyとテストはshared/ui/Buttonに保持する。ActionButtonは独自propsから既存Button/SpectrumButtonへの変換を担当する。単なる再exportの中継は追加していない。移動した評価・タグ・候補ポップアップのスタイル宣言値は維持した。

## 実施した検証

| 層 | 結果 |
|---|---|
| 共通quick・full | 成功。受入条件は`tmp/quality/task.json`、最終レポートは`tmp/quality/result.json` |
| 型・Biome lint/format・StyleX lint | 成功 |
| frontend Node unit | 152件成功、skipなし。別実行のPython連携unitも1件成功 |
| 境界の回帰 | 相対・alias・型参照・再export・dynamic import・helperによる迂回を拒否。componentのライブラリ直接importも拒否 |
| 共有Storybookブラウザー | 12件成功。入力補完、続けて入力、外部からの内容復元、文字数制限、評価選択とキーボード、既存共有UIを確認 |
| Storybook静的ビルド | 成功 |
| productionビルド・HTTP・Chromium | 15件成功。ログイン入力、HTTP契約、390px/1280pxのレイアウト、4000/4001文字の制限を確認 |
| 対象モックE2E | 認証期限切れ・評価・薬剤入力の24件成功。評価の取消・失敗復元・再試行・reduced motion、薬剤補完・タグ削除・送信・50/51件制限・未送信質問の復元を含む |

新規Story検査の初回は、ロード待機とテスト側で想定した操作・ARIAロールに誤りがあり失敗した。ロード待機を明示し、矢印によるフォーカス移動後のEnter操作と補完のmenuitemロールに修正して12件成功を確認した。失敗を本番UIの成功として数えていない。

## デザイン比較

変更前にビルドした実画面と変更後の実画面を、同じモック・フォント条件、390px/1280pxで撮影した。チャット入力・薬剤候補・回答・登録・検索・ログインの12枚を比較し、11枚はピクセル完全一致。

残るdesktop回答の1枚はメッセージ領域が縦1px移動しており、4403ピクセルが相違した。その領域の縦位置を1px揃えた比較では相違0で、領域外も一致した。スクロール状態を含む撮影結果の差として記録し、12枚すべての完全一致とは報告しない。比較データは`tmp/layer-migration/visual-comparison.json`、画像は同ディレクトリの`before`と`after`に置いた。

## 残る制約

`TC-K01`も別実行し、同一YJコードの候補でReact keyが重複し、初期選択待ちが30秒で失敗することを確認した。これは[前回の検証記録](ui-component-folders-validation.md)にもある未解決ケースで、今回の24件成功とは分ける。テストの削除や期待値変更は行っていない。

共通fullは静的検査・unitの成功であり、ブラウザー全体の成功ではない。今回、全E2E・configured PostgreSQL起動・実backend接続・外部LLMは実行していない。ブラウザー検証は固定API/WebSocketを使っており、実データや外部サービスとの統合成功を示さない。
