"use client";

import * as stylex from "@stylexjs/stylex";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { styles } from "./AppHeader.styles";

interface AppHeaderProps {
  children?: ReactNode;
}

export function AppHeader({ children }: AppHeaderProps) {
  const pathname = usePathname();

  const isChat = pathname === "/" || pathname === "";
  const isSearch = pathname?.startsWith("/search");
  const isImports = pathname?.startsWith("/imports");

  return (
    <header {...stylex.props(styles.header)}>
      <div {...stylex.props(styles.leftSection)}>
        <Link href="/" {...stylex.props(styles.titleLink)}>
          <h1 {...stylex.props(styles.title)}>薬剤師向け 添付文書検索</h1>
        </Link>
        <nav {...stylex.props(styles.nav)} aria-label="メインナビゲーション">
          <Link
            href="/"
            aria-label="チャットへ戻る"
            {...stylex.props(styles.navLink, isChat && styles.activeNavLink)}
            aria-current={isChat ? "page" : undefined}
          >
            チャット
          </Link>
          <Link
            href="/search"
            aria-label="キーワード検索"
            {...stylex.props(styles.navLink, isSearch && styles.activeNavLink)}
            aria-current={isSearch ? "page" : undefined}
          >
            キーワード検索
          </Link>
          <Link
            href="/imports"
            aria-label="添付文書XMLを取り込む"
            {...stylex.props(styles.navLink, isImports && styles.activeNavLink)}
            aria-current={isImports ? "page" : undefined}
          >
            XML取り込み
          </Link>
        </nav>
      </div>
      {children && <div {...stylex.props(styles.rightSection)}>{children}</div>}
    </header>
  );
}
