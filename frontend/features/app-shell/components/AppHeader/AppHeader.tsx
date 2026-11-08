"use client";
import * as stylex from "@stylexjs/stylex";
import { Pill } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Header } from "../../../../shared/component/Header";
import { LogoutButton } from "../../../authentication/components/LogoutButton";
import { styles } from "./AppHeader.styles";

interface AppHeaderProps {
  children?: ReactNode;
  connectionStatus?: ReactNode;
  connectionNotice?: ReactNode;
}
export function AppHeader({
  children,
  connectionStatus,
  connectionNotice,
}: AppHeaderProps) {
  const pathname = usePathname();
  const isChat = pathname === "/" || pathname === "";
  const isSearch = pathname?.startsWith("/search");
  const isImports = pathname?.startsWith("/imports");
  const isGuide = pathname?.startsWith("/guide");
  const navigation = (isMobile: boolean, close?: () => void) => (
    <nav
      {...stylex.props(isMobile ? styles.sheetNav : styles.nav)}
      aria-label="メインナビゲーション"
    >
      <Link
        onNavigate={close}
        href="/"
        aria-label="チャットへ戻る"
        {...stylex.props(
          styles.navLink,
          isMobile && styles.sheetLink,
          isChat && (isMobile ? styles.activeSheetLink : styles.activeNavLink),
        )}
        aria-current={isChat ? "page" : undefined}
      >
        チャット
      </Link>
      <Link
        onNavigate={close}
        href="/search"
        aria-label="キーワード検索"
        {...stylex.props(
          styles.navLink,
          isMobile && styles.sheetLink,
          isSearch && (isMobile ? styles.activeSheetLink : styles.activeNavLink),
        )}
        aria-current={isSearch ? "page" : undefined}
      >
        キーワード検索
      </Link>
      <Link
        onNavigate={close}
        href="/imports"
        aria-label="添付文書XMLを取り込む"
        {...stylex.props(
          styles.navLink,
          isMobile && styles.sheetLink,
          isImports && (isMobile ? styles.activeSheetLink : styles.activeNavLink),
        )}
        aria-current={isImports ? "page" : undefined}
      >
        添付文書登録
      </Link>
      <Link
        onNavigate={close}
        href="/guide"
        {...stylex.props(
          styles.navLink,
          isMobile && styles.sheetLink,
          isGuide && (isMobile ? styles.activeSheetLink : styles.activeNavLink),
        )}
        aria-current={isGuide ? "page" : undefined}
      >
        検索の仕組み
      </Link>
    </nav>
  );

  return (
    <Header
      brand={
        <Link href="/" {...stylex.props(styles.titleLink)}>
          <span {...stylex.props(styles.logoBadge)}>
            <Pill size={16} color="var(--user-bg)" strokeWidth={2.2} />
          </span>
          <h1 {...stylex.props(styles.title)}>薬剤師向け 添付文書検索</h1>
        </Link>
      }
      renderNavigation={navigation}
      actions={<LogoutButton />}
      controlsLabel="回答設定"
      connectionStatus={connectionStatus}
      connectionNotice={connectionNotice}
    >
      {children}
    </Header>
  );
}
