# featureのコンポーネント別配置

既存の未コミット差分を基準に、featureの表示部品を`components/<部品名>/`へ集約した。実装・専用スタイル・Story・テストを同じフォルダへ置き、部品ごとのindexを入口にした。

## 配置

| 対象 | 配置後 |
|---|---|
| chatのChatScreen、ChatHeader、ChatInputForm、AnswerFeedback、AssistantMarkdown、MessageItem、MessageList、JevResponseInspector、ExpandableEvidenceContent、SourceEvidence各部品 | `features/chat/components/<部品名>/` |
| AppHeader | `features/app-shell/components/AppHeader/` |
| AuthBoundary、LoginScreen、LogoutButton | `features/authentication/components/<部品名>/` |
| KeywordSearchScreen、SearchGuideScreen | 各featureの`components/<部品名>/` |
| MedicineAutocompleteInput、MedicinePicker、MedicinePromptDock、MedicinePromptField | `features/medicine-selection/components/<部品名>/` |
| ImportScreen、ImportHistory | `features/package-insert-import/components/<部品名>/` |
| SourceEvidenceCard/PanelのStory | 対応する部品フォルダ |
| SourceEvidenceFilters.test.mjs | `SourceEvidenceSectionFilters/SourceEvidenceSectionFilters.test.mjs` |
| sample-evidence-units.json | `SourceEvidenceContent/fixtures/sample-evidence-units.json` |
| 根拠表示の共通CSS | `features/chat/styles/markdown-content.css` |
| 複数Storyの共通データ | `features/chat/fixtures/packageInsertData.ts` |

57ファイルの移動対応表は`tmp/feature-component-folders/moves.json`。API・model・hooksの配置とfeatureの公開範囲は維持した。旧パスへの互換ファイルは追加していない。

source-data suiteの登録、品質ハーネスの回帰検査、Storyデータの生成先、Next/StorybookのCSS読込も更新した。品質ハーネスのテスト探索確認は、削除済みのGit追跡パスを対象から外し、存在する未追跡テストも含めて検査するよう修正した。現存テストの検査範囲は縮めていない。

## 検証

| 検証 | 結果 |
|---|---|
| 移動したTS/TSXの比較 | 50ファイルでimportを除いたASTが一致。表示・処理・スタイル宣言の変更なし |
| CSS・部品専用JSON fixture | 移動前とバイト一致 |
| 共通quick | 修正後に成功 |
| frontendの型・lint・StyleX lint・依存境界 | 成功 |
| frontend Node unit | 152件成功、skipなし |
| Python連携unit | 1件成功 |
| 品質ハーネスの対象回帰 | quality/quality-specの28件成功、skipなし |
| Storybook | 静的ビルド成功、共有UIブラウザー12件成功 |
| 本番ビルド・HTTP・Chromium | 15件成功 |
| 本番画面の変更前後比較 | 390px/1280pxの12枚中11枚でピクセル完全一致。desktop入力画面1枚は12ピクセル差が残る。画像全体の完全一致とは扱わない |

作業specは`tmp/quality/task.json`、共通fullの結果は`tmp/quality/result.json`を正本とする。共通fullでは、登録済みPostgreSQLへの接続ができず、backendテストも時間内に完了しなかったため、全体成功とはしていない。frontendのformat違反は修正後に単独再検査し成功を確認した。toolingテストにはOSシグナル検査2件のskipがあるため、それらを成功件数へ加えていない。

画像・移動表・ソース比較の証跡は`tmp/feature-component-folders/`。Storyとスクリーンショットは固定API/WebSocketを使っており、実backend・外部LLMとの統合成功を示さない。source-data suiteは移動先への登録を回帰検査したが、実原本を使う当該suiteは実行していない。
