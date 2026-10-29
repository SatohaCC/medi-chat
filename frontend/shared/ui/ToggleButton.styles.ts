import * as stylex from "@stylexjs/stylex";
export const styles = stylex.create({
  base: {
    minHeight: { default: "auto", "@media (max-width: 600px)": "44px" },
    paddingBlock: "4px",
    paddingInline: "10px",
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
    borderColor: "rgba(2, 101, 220, 0.35)",
    backgroundColor: "rgba(2, 101, 220, 0.12)",
    color: "#0265dc",
    fontWeight: 600,
  },
  customSelected: {
    borderColor: "rgba(13, 130, 83, 0.35)",
    backgroundColor: "rgba(13, 130, 83, 0.12)",
    color: "#0d8253",
    fontWeight: 600,
  },
  unregistered: {
    borderStyle: "dashed",
    borderColor: "rgba(245, 158, 11, 0.6)",
    color: "#b45309",
  },
  unregisteredSelected: {
    borderStyle: "dashed",
    borderColor: "#f59e0b",
    backgroundColor: "rgba(245, 158, 11, 0.15)",
    color: "#b45309",
    fontWeight: 600,
  },
  disabled: { opacity: 0.5, cursor: "not-allowed" },
});
