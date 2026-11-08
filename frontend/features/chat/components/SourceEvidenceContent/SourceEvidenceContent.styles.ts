import * as stylex from "@stylexjs/stylex";
export const styles = stylex.create({
  content: {
    paddingBlock: "var(--space-3)",
    paddingInline: "var(--space-1)",
    color: "var(--fg)",
    fontSize: "14px",
    lineHeight: 1.75,
  },
  tableScroll: {
    maxWidth: "100%",
    overflowX: "auto",
    borderWidth: "1px",
    borderStyle: "solid",
    borderColor: "var(--border)",
    borderRadius: 0,
    scrollbarWidth: "thin",
    outlineWidth: { default: null, ":focus-visible": "2px" },
    outlineStyle: { default: null, ":focus-visible": "solid" },
    outlineColor: { default: null, ":focus-visible": "var(--user-bg)" },
    outlineOffset: { default: null, ":focus-visible": "2px" },
  },
  markdown: { minWidth: "0", whiteSpace: "normal", overflowWrap: "anywhere" },
});
