import * as stylex from "@stylexjs/stylex";
export const styles = stylex.create({
  base: {
    minHeight: { default: "auto", "@media (max-width: 600px)": "44px" },
    paddingBlock: "var(--space-1)",
    paddingInline: "var(--space-3)",
    borderRadius: 14,
    borderWidth: 1,
    borderStyle: "solid",
    borderColor: "var(--border)",
    backgroundColor: "transparent",
    color: "var(--fg)",
    fontSize: 12,
    cursor: "pointer",
    transition: "all 0.15s ease",
  },
  selected: {
    borderColor: "var(--accent-border)",
    backgroundColor: "var(--accent-hover)",
    color: "var(--user-bg)",
    fontWeight: 600,
  },
  customSelected: {
    borderColor: "var(--success-border)",
    backgroundColor: "var(--success-bg)",
    color: "var(--success-fg)",
    fontWeight: 600,
  },
  unregistered: {
    borderStyle: "dashed",
    borderColor: "rgba(245, 158, 11, 0.6)",
    color: "var(--pending-fg)",
  },
  unregisteredSelected: {
    borderStyle: "dashed",
    borderColor: "#f59e0b",
    backgroundColor: "var(--pending-bg)",
    color: "var(--pending-fg)",
    fontWeight: 600,
  },
  disabled: { opacity: 0.5, cursor: "not-allowed" },
});
