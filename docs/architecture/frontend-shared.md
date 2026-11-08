# frontendの共有UIと依存境界

`shared`にはドメインに依存しない部品を置く。複数画面で使うことだけを理由に、認証・医薬品・チャット等の処理をsharedへ置かない。

| 配置 | 責務 |
|---|---|
| `frontend/shared/ui` | 基本UIと、使用中のUIライブラリの部品単位の公開入口 |
| `frontend/shared/component` | 基本UIを組み合わせた汎用表示。Header、PageLayout、Tabs、Disclosure、テキスト表示など |
| `frontend/shared/hooks` | ドメインに依存しない表示・ブラウザー同期 |
| `frontend/shared/providers` | UIライブラリのProvider |
| `frontend/shared/api` | 汎用的な接続先解決。機能固有のURLやセッション状態は置かない |
| `frontend/features` | ドメインの型・判断・通信・状態と、sharedへの接続 |

依存方向は`app → features → shared/component → shared/ui`とする。表示用スタイルや汎用Hookはsharedから利用できる。

- sharedからfeatures・appへ依存しない。型参照・再export・間接参照も対象。
- shared/ui・shared/componentからshared/apiへ依存しない。Hook等を経由しても同じ。
- shared/uiからshared/componentへ依存しない。
- UI内部からNext.jsのRouterを読み取らない。ルートと現在位置の判断は呼び出し側に置く。
- features・appはshared/componentを通して表示部品を使い、shared/uiを直接参照しない。componentは独自のpropsで操作・選択・入力値を受け取り、UIライブラリのイベント・Selection・Context・クラスをfeatureへ公開しない。
- UIライブラリの直接importはshared/uiとProviderに閉じる。componentはshared/uiの入口を使って組み立てと変換を担い、単なる再exportの中継を作らない。
- PromptDocumentはライブラリ非依存の入力スナップショット。ネイティブのカーソル・選択状態はTokenPromptInput内で保持し、薬剤候補の検索とトークン内容の決定はmedicine-selectionが担う。

## 表示と接続の分離

Headerにはブランド、ナビゲーションの描画、操作領域、設定を渡す。アプリ名、画面一覧、現在のルートは`features/app-shell`で組み立て、LogoutButtonはauthenticationが提供する。

認証APIと共有セッション状態の正本は`features/authentication/api.ts`。複数featureから同じモジュールを利用し、状態やrefresh処理を複製しない。WebSocketの機能固有URLと文字数制限はchatが所有する。入力部品に必要な制限はpropsで渡す。

表示内で完結する展開やフォーカスの状態は共有UIに置ける。ユーザー操作はイベントハンドラ、外部同期はEffectで扱う。custom Hookの抽出だけでは状態共有や表示の独立性を保証しない。

variantやtoneは`compact`、`surface`、`positive`等の見た目を表す。医薬品・根拠・Jev等の用途との対応はfeatureで決める。選択状態を持つ操作はToggleButton、通常の操作はButtonを使う。

汎用MarkdownとハイライトのCSSはそれぞれ`shared/component/MarkdownContent/MarkdownContent.css`・`shared/component/HighlightText/HighlightText.css`、根拠の表など専用CSSはchatに置く。アプリのlayoutとStorybookで必要なスタイルを読み込む。

## 検証

`frontend/scripts/shared-boundaries.test.mjs`は、TypeScriptのモジュール解決を使い、相対・エイリアス・型参照・再export・静的dynamic import・JSON/CSSの依存を検査する。負例と本番ソースの両方を共通品質ハーネスで実行する。実行時に計算される依存関係や、ドメイン用語の意味までは証明しないため、公開propsのレビューも行う。

- `pnpm --filter frontend lint:boundaries`: 依存境界だけの確認。
- `pnpm agent:check --phase quick`と完了前のfull: 作業specによる受入検査と回帰検査。
- `pnpm --filter frontend test:e2e:shared`: ポート6007の独立したStorybookで、共有UIの操作・キーボード・フォーカス・業務API呼び出しのないことを検証。
- `pnpm build-storybook`: featuresとsharedのStoryをビルド。
- 実画面のE2E・visual regression・SSR/HMR・productionのCSS確認は別に実施し、単体検査やStorybookの成功で代替しない。

共有UIのStoryは`frontend/shared`配下の`*.stories.tsx`に置き、業務モデルや認証Providerを必要としないデータで動かす。

## 部品ごとの配置

基本UIは`shared/ui/Button/`のように部品名のフォルダへ集約する。複合表示も`shared/component/Header/`のように同じ規則で配置する。

feature内の表示部品も`features/<feature>/components/<部品名>/`へ集約する。実装・専用スタイル・Story・単体テスト・部品専用fixtureを同じフォルダに置き、`index.ts`を公開入口とする。テストファイルは対象部品の名前に揃える。別featureからは既存のfeature公開入口を使い、フォルダ化を理由に公開範囲を広げない。

複数の部品が使うfeature固有のCSSはfeature内の`styles`、複数Storyの共通データは`fixtures`に置く。hooks・model・apiは責務を保ち、部品フォルダへまとめるためだけに移動しない。ファイル移動時はimportだけでなく、CSS読込・Story生成先・明示的なテスト登録・`new URL(..., import.meta.url)`の参照も更新する。旧パスの互換ファイルは残さない。

```text
shared/ui/Button/
  index.ts
  Button.tsx
  Button.styles.ts
  Button.stories.tsx
  Button.test.mjs
  Button.browser.spec.ts
```

`index.ts`は部品単位の公開入口とし、component層は`shared/ui/Button`を参照し、feature層は`shared/component/ActionButton`を参照する。Buttonは独自UI・SpectrumButton・AriaButtonを同じ入口から公開し、既存のAPIと見た目はそれぞれ維持する。ライブラリの部品はindexから直接再exportし、中継だけのファイルを追加しない。公開するコンポーネント・型は明示し、`export *`でライブラリ全体を公開しない。ToggleButtonも同じ方針とする。旧ファイル名での互換入口は置かない。

実装・スタイル・Story・単体テスト・部品単独のブラウザーテストは、その部品のフォルダに置く。ネイティブUIの単純な再exportだけの部品は`index.ts`を入口とし、実装を複製したり、配置を埋めるだけのテストを追加したりしない。画面間の統合検査は既存のE2E配置に置く。

共有UIの単独ブラウザーテストは`shared/**/*.browser.spec.ts`を`playwright.shared.config.ts`で実行する。Storyは同じフォルダの`*.stories.tsx`をStorybookの再帰探索で読み込む。
