import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "薬剤師向け 添付文書検索",
  description: "医療用医薬品の電子添文を検索し、根拠を確認するチャット",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  );
}
