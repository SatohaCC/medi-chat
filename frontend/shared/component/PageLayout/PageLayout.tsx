import * as stylex from "@stylexjs/stylex";
import type { ReactNode } from "react";
import { styles } from "./PageLayout.styles";
export function PageLayout({
  children,
  screen,
}: {
  children: ReactNode;
  screen?: string;
}) {
  return (
    <div {...stylex.props(styles.root)} data-screen={screen}>
      {children}
    </div>
  );
}
export function PageWorkspace({ children }: { children: ReactNode }) {
  return <div {...stylex.props(styles.workspace)}>{children}</div>;
}
