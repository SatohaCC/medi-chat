# 共有UIの部品別フォルダ集約

## 配置

`frontend/shared/ui/Button/`へ独自Button・SpectrumButton・AriaButtonの実装と公開入口を集約した。ToggleButtonも同様に集約し、他の基本UIは部品名フォルダの`index.ts`から公開する。複合表示は`frontend/shared/component/<部品名>/`へ配置した。

各部品の実装・スタイル・Story・単体テスト・単独ブラウザーテストを同じフォルダに置き、混在していたSharedComponentsのStoryとSharedPresentationのテストを分割した。画面間の統合テストは既存のE2E配置に維持する。

## デザイン維持の確認

この配置変更の直前の作業ツリーを比較対象にした。前のUI分離作業や利用者の差分をHEADへ戻して比較していない。

- Button、ToggleButton、Tabs、Disclosure、Header、PageLayout、MarkdownContent、HighlightTextを390px・1280pxで撮影。390pxのHeaderメニュー展開も含め、17パターンすべて移動前後の変更ピクセル数は0。
- フォント条件・viewport・スクリーンショット時のアニメーション条件を揃え、画素値を比較した。既存の期待画像を更新して成功にはしていない。
- 独自実装とStyleX定義14ファイルを、import宣言を除いたTypeScript ASTの出力で比較し、すべて一致した。色・寸法・余白・状態分岐の変更は含まない。

証跡はGit管理外の`tmp/ui-folder-work/before-visual.json`・`after-visual.json`・`implementation-comparison.json`と、同ディレクトリのbefore/after画像に保存した。この比較は対象Storyと条件の範囲を検証し、全画面の全状態を網羅したものではない。

## 検証結果

| 検証 | 結果 |
|---|---|
| 共通quick | 成功 |
| frontend単体 | 144件成功、skipなし |
| 型・lint・format・StyleX lint・依存境界 | 成功 |
| 部品別Storybookブラウザー | 6件成功。Button各実装、ToggleButton、Tabs、Disclosure、Headerのキーボード・開閉・フォーカスを確認 |
| 本番ビルド・HTTP・ブラウザー | 15件成功。既存HTTP契約と390px・1280pxのレイアウト・文字数制限を確認 |
| Storybook静的ビルド | 成功。部品フォルダ内のStoryを出力 |
| 共通full | browser suiteが300秒でtimeoutし、全体は失敗。最終結果は`tmp/quality/result.json` |

型・lint・format・依存境界と、再帰配置されたテストの実行対象も共通ハーネスで確認する。ブラウザーの個別検証は固定API/WSを使うため、外部LLMや実接続全体の成功は示さない。前回の全E2E未解決事項は[前回の検証記録](frontend-shared-ui-validation.md)に記載している。

fullの診断には前回と同じ取り込み履歴・取り込み結果、および`TC-K01`の医薬品候補重複キーが残った。タイムアウトを延ばしたり、検査を除外して成功にはしていない。停止したbrowser層と待ち条件をログで確認した。今回の配置変更前後の見た目・実装一致と、全E2Eの未解決事項を分けて評価する。
