# 表示と状態・通信の責務分割

`react-presentational-container` Skillに沿い、画面の構成・業務状態・通信・表示内の状態を区別した。対象は責務の混在が大きかったChatScreen、KeywordSearchScreenと、表示の読み解きに負荷があったJevResponseInspector。

## 分割した責務

| 対象 | 構成と読む目的 |
|---|---|
| ChatScreen | `ChatScreen.tsx`が接続入口。`useChatScreen.ts`が単一WebSocket・根拠状態・送信を接続。`useChatDraft.ts`が薬剤選択・質問・送信後更新・未送信質問の復元を所有。`ChatScreenView.tsx`が画面配置、`ChatDeliveryStatus.tsx`が保留・取消・復元確認を描画 |
| KeywordSearchScreen | `useKeywordSearch.ts`が検索・二重送信防止・検索時点の条件と結果を保持。`KeywordSearchView.tsx`が配置し、`KeywordSearchForm`・`MedicineSearchFilter`・`KeywordSearchResults`が各表示を担当 |
| JevResponseInspector | `JevIntentHeading`・`JevIntentSummary`・`JevProbabilityDistribution`・`JevRawData`へ分割。意図の表示名・説明定数は`model/jevIntentMeta.ts`へ移し、他部品がInspectorの実装へ依存せず参照できるようにした |

既存のフォルダ単位の入口を維持し、実装・スタイル・Story・テストは同じ部品フォルダに置いた。表示は必要なデータと操作を受け取り、HTTPクライアントやtransport全体を渡さない。ルーティングに依存するヘッダーはContainerから表示へ渡す。画面の単独Storyではテスト用ヘッダーと固定propsを使う。

薬剤カタログ取得とWebSocketの呼び出し数は増やさず、既存Hookを一度ずつ接続する。Effectへユーザー操作を移していない。薬剤補完・検索API・送信payload・状態共有の方式・UIライブラリ・スタイル宣言は変更していない。

## 状態の所有者

- 下書き、対象薬、モデルと復元確認は`useChatDraft`。送信成功後だけ下書きを消去し、保留からの復元は明示操作で行う。
- 検索条件・実行中・検索結果・結果に対応する検索語は`useKeywordSearch`。医薬品選択肢の開閉だけは表示内の`MedicineSearchFilter`が持つ。
- Jevのタブ・確率分布の全件表示はInspectorが保持する。summaryタブの子へ全件表示の状態を移すとタブ切替で失われるため、表示データと操作を子へ渡す。

状態・通信を持たない表示や、すでに業務処理がHookへ分離されている部品には、Containerを機械的に追加していない。ファイル数と参照は増えるが、「画面の配置」「状態遷移」「通信への接続」「各表示」を別々に確認できる。行数やContainerの存在自体を受入条件にはしていない。

## 検証

| 層 | 結果 |
|---|---|
| 表示の単体テスト | 保留・取消・復元確認、確率値・不明キー・メタデータ、検索の初期・処理中・空・失敗の描画を確認。検索ViewはRouterなしで、render中のfetchを禁止して実行 |
| frontend全Node unit | 155件成功。Python連携unitは別実行で1件成功 |
| 型・lint・format・StyleX・境界検査 | 成功 |
| 関連モックE2E | 29件成功。単一送信、薬剤補完・削除・50/51件制限、保留・取消・期限切れ・モデルとトークンの復元、評価と認証を確認 |
| 本番ビルド・HTTP・Chromium | 17件成功。既存15件に加え、Jev全件表示のタブ往復とJSON値、検索の処理中・選択条件・失敗・再試行を確認 |
| デザイン比較 | 390px/1280px、入力・候補・回答・登録・検索・ログインの12枚でピクセル完全一致 |
| Storybookビルド | 成功。ChatScreenViewとKeywordSearchViewの単独Storyを追加 |

本番検査の新規検索テストは初回スイッチのclick待ちで失敗した。キーボードで選択しchecked状態を確認する検査に修正後、17件成功を確認した。最初の失敗を成功に数えていない。

共通quickとfullを実行し、結果は`tmp/quality/result.json`に記録する。共通fullは既存のbackend起動確認に必要なPostgreSQLへ接続できず、backendテストもタイムアウトしたため、全体成功として扱わない。toolingのOSシグナル検査2件のskipも成功に含めない。

全E2E、実backend・実DB・外部LLMとの統合は今回の成功範囲ではない。既知の候補重複キー`TC-K01`は修正しておらず、今回の29件から除外している。作業specは`tmp/quality/task.json`、画像・比較結果・分割前ソースは`tmp/presentation-split/`に保存した。

## 追記（2026-11-08）

`TC-K01`を修正した。処方薬ピッカーの選択肢IDがYJコードだけで、YJコードを共有する製品があると候補一覧のキーが衝突し、候補が描画されなかった。IDをYJコード・製品名・位置から作るよう変更し、E2Eの初期セットアップも既定の対象薬を含むフィクスチャへ修正した。修正前の実装で同テストが失敗し、修正後に`e2e/medicine-mention.spec.ts`の14件が成功することを確認している。回帰は`features/medicine-selection/model/medicinePickerOptions.test.mjs`が確認する。
