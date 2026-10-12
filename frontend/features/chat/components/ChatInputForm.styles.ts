import * as stylex from "@stylexjs/stylex";
export const styles = stylex.create({
  inputSlot: { flex: "1", minWidth: 0, display: "flex" },
  form: {
    display: "flex",
    gap: "8px",
    paddingBlock: "16px",
    paddingInline: "20px",
    borderTopWidth: "1px",
    borderTopStyle: "solid",
    borderTopColor: "var(--border)",
  },
});
