import * as stylex from "@stylexjs/stylex";

const blink = stylex.keyframes({ "50%": { opacity: 0 } });
export const styles = stylex.create({
  userText: { whiteSpace: "pre-wrap" },
  statusText: { marginTop: "6px", fontSize: "12px", color: "var(--muted)" },
  message: { display: "flex" },
  user: { justifyContent: "flex-end", scrollMarginTop: "12px" },
  withSources: {
    display: { default: "grid", "@media (max-width: 900px)": "flex" },
    gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)",
    alignItems: "start",
    gap: "16px",
    flexDirection: { default: null, "@media (max-width: 900px)": "column" },
  },
  bubble: {
    maxWidth: "80%",
    paddingBlock: "10px",
    paddingInline: "14px",
    borderRadius: "12px",
    fontSize: "15px",
    lineHeight: 1.5,
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  },
  markdown: { minWidth: "0", whiteSpace: "normal", overflowWrap: "anywhere" },
  userBubble: {
    backgroundColor: "var(--user-bg)",
    color: "var(--user-fg)",
    borderBottomRightRadius: "4px",
  },
  assistantBubble: {
    backgroundColor: "var(--assistant-bg)",
    borderBottomLeftRadius: "4px",
  },
  errorBubble: { color: "var(--error)" },
  evidenceBubble: {
    maxWidth: "none",
    minWidth: "0",
    width: "100%",
  },
  cursor: {
    display: "inline-block",
    width: "2px",
    height: "1em",
    backgroundColor: "var(--fg)",
    marginLeft: "2px",
    verticalAlign: "text-bottom",
    animationName: blink,
    animationDuration: "0.8s",
    animationTimingFunction: "step-end",
    animationIterationCount: "infinite",
  },
});
