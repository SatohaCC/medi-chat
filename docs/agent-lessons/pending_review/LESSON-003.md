# LESSON-003: StyleX導入で開発時のCSS抽出と設定パス解決を見落とした

- 状態: pending_review
- 作成日: 2026-10-12
- 最終確認日: 2026-10-12
- 承認者・承認日・承認の参照: 未承認
- 更新案の場合の対象: なし
- 統合先・廃止理由: なし

## 本文を読むトリガー条件

Next.jsのTurbopackでStyleX/PostCSSを導入・変更する場合、生成クラスはあるが装飾されない場合、設定内のパスが仮想パスになりソースglobが0件になる場合。

## 適用する条件／適用しない条件

今回確認したNext.js 16.3.6、StyleX 0.19.1、Tailwind PostCSS共存のWindows開発環境に適用する。別版・別bundlerで同じ原因と断定しない。CSSの優先順位・ネットワーク取得失敗・別の依存競合には原因の確認なしで処理順変更を適用しない。

## 観察した失敗と証拠

生成クラスがButtonへ付いた一方、実ブラウザで背景・余白・文字サイズが未装飾だった。developmentの直接PostCSS比較ではTailwind→StyleXがCSSを抽出せず、StyleX→Tailwindで抽出した。NODE_ENV未指定の比較だけでは再現を見逃した。

Turbopackの設定処理ではディレクトリURLがモジュール解決の対象になり、また設定内のrootが仮想パスまたは二重frontendパスとなった。ソース位置から実在設定ファイルを確認する解決に修理した。

- 証跡: `for-llm/progress/20261012-stylex-react-aria-refactor-evidence/unit1-mock-css-fixed.log`、`unit1-root-diagnostic.log`、`unit1-dev-hmr-green.log`、`unit1-production-build.log`。
- 対象: `frontend/postcss.config.mjs`、`frontend/babel.config.js`、`frontend/e2e/stylex-build.spec.ts`、`frontend/e2e/stylex-hmr.spec.ts`。
- PR/コミット: 未作成。作業ツリー差分に対する証跡。

表示移行でも、`background`指定が型/StyleX lintを通る一方でBabel metadataに対応CSSが生成されない箇所を確認した。背景色/画像のlonghandへ分けて修理し、`unit4-inline-color-compare.log`の視覚比較22件が成功した。これは当該値・版の観察であり、すべてのbackground指定が非対応という結論ではない。

## 原因

- 確認済み: developmentにおけるPostCSS処理順と、Turbopack設定内のroot解決がCSS抽出へ影響した。
- 不確実性: 他版・他OSでの再現性は未確認。二つの原因を一般的なStyleX非互換として扱わない。
- 型/lint受理とCSS生成は別の観測。単位4の背景指定はmetadataとcomputed styleを併用して切分けた。一般的なshorthand禁止規則へ拡張しない。

## 次回の具体的な確認手順

1. development/productionを明示し、同じソースglobとBabelオプションで直接PostCSSの生成CSSを比較する。
2. 実在するfrontend設定位置と抽出対象を確認する。仮想パスやcwd依存の固定パスで成功へ寄せない。
3. devブラウザでcomputed style、JSなしSSR、hydration、隣接StyleXファイル編集/復元のHMRを観測する。入力・選択・timeOrigin/documentの保持も確認する。
4. production buildと同じ成果物をnext startで表示して同じ装飾を確認する。生成クラス・型検査・buildだけでCSS適用成功とはしない。

## 対策の検証

- 単位1: dev初回表示/HMR、production SSR/hydration、統合mock33件/real3件成功。Compiler/Turbopack維持。
- 実OS IME・全画面視覚比較は本記録の成功範囲に含まない。
- 回帰: `frontend/e2e/stylex-build.spec.ts`、`frontend/e2e/stylex-hmr.spec.ts`。今後ファイル移動時は利用側と証跡を追跡する。

## 次の関連作業での評価

未評価。承認待ちの観察・提案であり、INDEXへ登録せず作業規約として扱わない。
