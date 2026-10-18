import * as stylex from "@stylexjs/stylex";
export const styles = stylex.create({
  content: {
    paddingBlock: "10px",
    paddingInline: "4px",
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
    borderRadius: "8px",
    scrollbarWidth: "thin",
    outlineWidth: { default: null, ":focus-visible": "2px" },
    outlineStyle: { default: null, ":focus-visible": "solid" },
    outlineColor: { default: null, ":focus-visible": "#0265dc" },
    outlineOffset: { default: null, ":focus-visible": "2px" },
  },
  markdown: { minWidth: "0", whiteSpace: "normal", overflowWrap: "anywhere" },
});
