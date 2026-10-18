import type { Metadata } from "next";
import "./globals.css";
import { S2ClientProvider } from "@/shared/providers/S2ClientProvider";

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
      <body>
        <S2ClientProvider>{children}</S2ClientProvider>
      </body>
    </html>
  );
}
