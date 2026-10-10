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

Chromiumで質問送信、回答のストリーミングと根拠表示、会話履歴、
エラーからの回復、切断・再接続を検証します。専用のNext.js開発サーバーを
`127.0.0.1:3100`で自動起動するため、そのポートを空けてください。
医薬品APIとチャットWebSocketはPlaywrightでモック化し、バックエンド・DB・
外部LLM・APIキーは使用しません。実バックエンドまで通すE2Eとは別の検証です。
失敗時のスクリーンショットとtraceは`frontend/test-results/`へ保存します。

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
