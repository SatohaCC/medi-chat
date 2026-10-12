This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## チャットのPlaywrightテスト

リポジトリルートで実行します。

```bash
pnpm --filter frontend exec playwright install chromium
pnpm test:e2e
```

`pnpm test:e2e` はconfigured索引のread-only readinessと実OS health（3212）、
モックChromium（Next 3100）、実接続Chromium（Next 3110 / backend 3211）を
順に検証します。いずれかの必須層が失敗すると全体が非0になります。
実接続層は試験所有の一時SQLite・原本copyと固定外部SDKを使います。
運用データを書き換えず、実LLM通信は検証しません。
単独実行は `pnpm --filter frontend test:e2e:mock` / `test:e2e:real` です。
モック層の医薬品RESTとチャットWebSocketはPlaywright doubleであり、
実backend/DBの検証とは区別します。専用ポートを空けて実行してください。
失敗時のスクリーンショットとtraceは`frontend/test-results/`へ保存します。

## 共通UIとStyleX（移行中）

画面は `features/chat` / `features/medicine-selection` / `features/attachment-import`
の公開entryからrouteへ接続します。model/hooks/apiはRAC/StyleXに依存せず、接続先は
`shared/api/endpoints.ts` が解決します。Jev型はchat model、薬剤型はmedicine-selection modelの所有です。

RACは `shared/ui` のButton/ToggleButton/Select/Tabs/Disclosureで内包し、自前Propsへ
標準の値・boolean・callbackだけを公開します。交換時はこのwrapperを変更します。
単語補完は既存hookとDOM input refの範囲置換を保持しています。

StyleXは表示TSX・隣接 `*.styles.ts` と `styles/tokens.stylex.ts` に限定します。
`styles/tokens.css` が共通値の正典です。交換対象は表示層とBabel/PostCSS/lint設定で、
model/hooks/apiと意味的Propsは維持します。`app/globals.css` は単一`@stylex`入口です。
CSSはtokens、`styles/base.css` のreset/body、`features/chat/components/markdown-content.css`
の生成Markdown子孫だけです。原文HTMLへ入力styleを許可せず、表示枠のdynamic StyleXと分けます。

Tailwindは未使用確認後に依存/PostCSSを除去しました。`babel.config.js` のnext/babelと
StyleX、設定ファイル位置基準のPostCSS resolver、Turbopack・React Compiler・distDir分離を維持します。

```bash
pnpm typecheck:frontend
pnpm --filter frontend exec biome check .
pnpm --filter frontend lint:stylex
node --test frontend/scripts/semantic-compare.test.mjs
```

固定semantic oracleは原XMLの独立レビュー済みfixtureで、自動更新しません。
合成compositionイベントはOSの実IME操作の代替にはなりません。
Windows Microsoft IMEの旧HEAD/current手動記録は[専用手順](manual-e2e/README.md)と
`pnpm --filter frontend test:ime:manual`を使います。記録workflow成功と実IMEの前後合格は別です。
HMR回帰はButton隣接styleの色を一時変更し、終了時に元の内容へ復元します。

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
