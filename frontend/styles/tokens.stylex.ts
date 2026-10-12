import * as stylex from "@stylexjs/stylex";

// CSS owns the values; this bridge only references the existing semantic tokens.
export const tokens = stylex.defineVars({
  actionBackground: "var(--user-bg)",
  actionForeground: "var(--user-fg)",
  actionHoverBackground: "var(--action-hover-bg)",
  controlPaddingBlock: "var(--control-padding-block)",
  controlPaddingInline: "var(--control-padding-inline)",
  controlRadius: "var(--control-radius)",
  controlFontSize: "var(--control-font-size)",
  controlFontWeight: "var(--control-font-weight)",
});
