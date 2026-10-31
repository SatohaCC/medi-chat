"use client";

import * as stylex from "@stylexjs/stylex";
import { Menu, Pill, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import {
  Button,
  Heading,
  Sheet,
  SheetBackdrop,
  SheetContent,
  SheetOverlay,
  SheetTrigger,
} from "react-aria-components";
import { useMobileLayout } from "../hooks/useMobileLayout";
import { styles } from "./AppHeader.styles";
import { LogoutButton } from "./LogoutButton";

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
  const isMobile = useMobileLayout();

  const isChat = pathname === "/" || pathname === "";
  const isSearch = pathname?.startsWith("/search");
  const isImports = pathname?.startsWith("/imports");
  const isGuide = pathname?.startsWith("/guide");

  const navigation = (close?: () => void) => (
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
        XML取り込み
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
    <header {...stylex.props(styles.header)}>
      <Link href="/" {...stylex.props(styles.titleLink)}>
        <span {...stylex.props(styles.logoBadge)}>
          <Pill size={16} color="var(--user-bg)" strokeWidth={2.2} />
        </span>
        <h1 {...stylex.props(styles.title)}>薬剤師向け 添付文書検索</h1>
      </Link>
      {!isMobile && navigation()}
      {isMobile ? (
        <>
          <SheetTrigger>
            <Button aria-label="メニューを開く" {...stylex.props(styles.menuButton)}>
              <Menu size={22} />
            </Button>
            <SheetOverlay position="end" {...stylex.props(styles.sheetOverlay)}>
              <SheetBackdrop {...stylex.props(styles.sheetBackdrop)} />
              <Sheet {...stylex.props(styles.sheet)}>
                <SheetContent {...stylex.props(styles.sheetContent)}>
                  {({ close }) => (
                    <>
                      <div {...stylex.props(styles.sheetHeading)}>
                        <Heading slot="title" {...stylex.props(styles.sheetTitle)}>
                          メニュー
                        </Heading>
                        <Button
                          slot="close"
                          aria-label="メニューを閉じる"
                          {...stylex.props(styles.menuButton)}
                        >
                          <X size={22} />
                        </Button>
                      </div>
                      {navigation(close)}
                      {children && (
                        <section
                          aria-label="回答設定"
                          {...stylex.props(styles.sheetSettings)}
                        >
                          {children}
                          {connectionStatus}
                        </section>
                      )}
                      <div {...stylex.props(styles.sheetFooter)}>
                        <LogoutButton />
                      </div>
                    </>
                  )}
                </SheetContent>
              </Sheet>
            </SheetOverlay>
          </SheetTrigger>
          {connectionNotice && (
            <div role="status" {...stylex.props(styles.connectionNotice)}>
              {connectionNotice}
            </div>
          )}
        </>
      ) : (
        <div {...stylex.props(styles.rightSection)}>
          {children}
          {connectionStatus}
          <LogoutButton />
        </div>
      )}
    </header>
  );
}
