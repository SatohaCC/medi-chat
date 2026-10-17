import * as stylex from "@stylexjs/stylex";
export const styles = stylex.create({
  base: {
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
  selected: { borderColor: "#3b82f6", backgroundColor: "#1d4ed8", color: "#fff" },
  customSelected: { borderColor: "#10b981", backgroundColor: "#065f46", color: "#fff" },
  unregistered: {
    borderStyle: "dashed",
    borderColor: "rgba(245, 158, 11, 0.6)",
    color: "#fbbf24",
  },
  unregisteredSelected: {
    borderStyle: "dashed",
    borderColor: "#f59e0b",
    backgroundColor: "rgba(245, 158, 11, 0.2)",
    color: "#fef3c7",
  },
  disabled: { opacity: 0.5, cursor: "not-allowed" },
});
