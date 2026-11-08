import * as stylex from "@stylexjs/stylex";
export const styles = stylex.create({
  inputSlot: { flex: "1", minWidth: 0, display: "flex" },
  form: {
    display: "flex",
    gap: "var(--space-2)",
    paddingBlock: "var(--space-4)",
    paddingInline: "var(--space-page)",
    borderTopWidth: "1px",
    borderTopStyle: "solid",
    borderTopColor: "var(--border)",
  },
});
