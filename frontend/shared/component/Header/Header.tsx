"use client";
import * as stylex from "@stylexjs/stylex";
import { Menu, X } from "lucide-react";
import type { ReactNode } from "react";
import { useMobileLayout } from "../../hooks/useMobileLayout";
import { AriaButton as Button } from "../../ui/Button";
import { Heading } from "../../ui/Heading";
import {
  Sheet,
  SheetBackdrop,
  SheetContent,
  SheetOverlay,
  SheetTrigger,
} from "../../ui/Sheet";
import { styles } from "./Header.styles";
export interface HeaderProps {
  brand: ReactNode;
  renderNavigation: (mobile: boolean, close?: () => void) => ReactNode;
  actions?: ReactNode;
  children?: ReactNode;
  controlsLabel?: string;
  connectionStatus?: ReactNode;
  connectionNotice?: ReactNode;
}
export function Header({
  brand,
  renderNavigation,
  actions,
  children,
  controlsLabel,
  connectionStatus,
  connectionNotice,
}: HeaderProps) {
  const isMobile = useMobileLayout();
  return (
    <header {...stylex.props(styles.header)}>
      {brand}
      {!isMobile && renderNavigation(isMobile)}
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
                      {renderNavigation(isMobile, close)}
                      {(children || connectionStatus) && (
                        <section
                          aria-label={controlsLabel}
                          {...stylex.props(styles.sheetSettings)}
                        >
                          {children}
                          {connectionStatus}
                        </section>
                      )}
                      <div {...stylex.props(styles.sheetFooter)}>{actions}</div>
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
          {actions}
        </div>
      )}
    </header>
  );
}
