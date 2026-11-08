import * as stylex from "@stylexjs/stylex";

export const styles = stylex.create({
  wrapper: {
    display: "flow-root",
    minWidth: 0,
    position: "relative",
  },
  clamped: {
    maxHeight: "150px",
    overflow: "hidden",
  },
  expanded: {
    maxHeight: "none",
    overflow: "visible",
  },
  fadeOverlay: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    height: "44px",
    backgroundImage:
      "linear-gradient(to bottom, rgba(250, 251, 252, 0) 0%, rgba(250, 251, 252, 0.95) 100%)",
    pointerEvents: "none",
  },
  buttonRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "flex-end",
    marginTop: "var(--space-2)",
  },
  toggleButton: {
    display: "inline-flex",
    alignItems: "center",
    gap: "var(--space-2)",
    paddingBlock: "var(--space-1)",
    paddingInline: "var(--space-3)",
    fontSize: "12px",
    fontWeight: 600,
    color: "var(--user-bg)",
    backgroundColor: {
      default: "#ffffff",
      ":hover": "rgba(2, 101, 220, 0.08)",
    },
    borderWidth: "1px",
    borderStyle: "solid",
    borderColor: "var(--accent-border)",
    borderRadius: "16px",
    boxShadow: "0 1px 2px rgba(2, 101, 220, 0.08)",
    cursor: "pointer",
    transition:
      "background-color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease",
  },
  collapseButton: {
    color: "var(--muted)",
    backgroundColor: {
      default: "#f8fafc",
      ":hover": "#f1f5f9",
    },
    borderColor: "rgba(0, 0, 0, 0.15)",
    boxShadow: "0 1px 2px rgba(0, 0, 0, 0.04)",
  },
  keywordBadge: {
    fontSize: "10px",
    fontWeight: 600,
    color: "#854d0e",
    backgroundColor: "rgba(234, 179, 8, 0.25)",
    paddingBlock: "var(--space-1)",
    paddingInline: "var(--space-2)",
    borderRadius: "8px",
    marginLeft: "var(--space-1)",
  },
});
