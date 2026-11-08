# 共有UI分離の検証記録

## 変更範囲

基本UIとUIライブラリの入口を`frontend/shared/ui`、汎用複合表示を`frontend/shared/component`へ整理した。Headerのブランド・ナビゲーション・操作領域を注入し、固定ルートはapp-shell、認証処理はauthentication、WebSocketのURLと文字数制限はchatが所有する。

依存境界検査・共有UIのStory・単独操作テスト・本番レイアウトと文字数制限のテストを追加した。4001文字の警告も非表示にしていた既存CSSを、`role="alert"`を除外するように修正した。

## 実施結果

| 検証 | 結果 |
|---|---|
| 共通quick検査 | 成功。受入単体検査とfrontend lintを実行 |
| frontend lint・format・StyleX lint・型検査 | 成功 |
| frontend Node単体 | 141件成功、skipなし |
| Node/Python連携単体 | 1件成功、skipなし |
| Storybook静的ビルド | 成功。共有UIのStoryも出力 |
| 独立Storybook / Chromium | 3件成功。基本操作、選択、Tabs、Disclosure、390px・1280pxのHeaderとフォーカスを確認 |
| 本番ビルド / HTTP・Chromium | 15件成功。既存HTTP契約13件と、390px・1280pxのレイアウト・CSS・4000/4001文字の境界2件 |
| 既存画面の対象E2E | 44件中18件成功・26件失敗。全体成功ではない |
| 共通full検査のbrowser suite | 300秒でtimeout。full全体は失敗。最終レポートは`tmp/quality/result.json` |

独立Storybookは業務API・Routerを使わない。実画面のブラウザー試験は認証・医薬品API・WebSocketの固定ダブルを使うため、実サービスや外部LLMとの通信成功を示さない。

## 変更前との比較

HEAD `1817fb3`をGit archiveから`tmp`に隔離展開し、同じインストール済み依存を参照して別ポート3105で比較した。隔離場所に合わせてPostCSSの解決先を絶対パス化した。製品ソースや期待画像は変更していない。

- 医薬品ピッカー、根拠表示、Jev操作の対象11件: 変更前でも10件失敗・1件成功。うちvisual regressionの1件は次の集合と重複する。
- visual regression全17件: 変更前でも17件失敗。
- 重複を除く26件は、変更後の失敗したテスト名と一致する。例としてピッカーの検索欄のaccessible name不一致、デスクトップで自動表示された根拠パネルへの操作、既存のgeometry/画像期待との差がある。
- full検査で検出された医薬品候補の重複キーも、変更前HEADの`TC-K01`で再現した（1件失敗）。比較ログは`tmp/shared-ui-baseline/baseline-duplicate-key.log`。

期待画像・受入条件を更新して成功にはしていない。既存失敗があるため、今回の結果から全画面の視覚的同一性や全E2E成功は主張しない。

共通fullのbrowser suiteでは通常設定PostgreSQLのreadinessとOS healthは成功した。その後のモックChromiumは123件のうち68件まで結果が出た時点で300秒の上限に達した。ログには取り込み履歴・取り込み結果の失敗、および医薬品候補の重複キーエラーもある。この全suiteの失敗すべてについて変更前比較を終えたわけではない。実接続Chromium層には到達しておらず、実接続の成功とは扱わない。診断候補に従って停止した層と待ち条件を確認し、上限や受入条件は緩めていない。

比較ログは`tmp/shared-ui-baseline/baseline-browser.log`と`baseline-visual.log`、本番検証ログは`tmp/ui-production-final.log`に保存した。通常権限でのサーバー起動は進まず中断し、ローカルサーバー・Chromium試験は権限拡張後に実施した。中断後の専用Next生成物を再生成してから、実画面の試験結果を取得した。
