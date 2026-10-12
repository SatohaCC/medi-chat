import * as stylex from "@stylexjs/stylex";
export const styles = stylex.create({
  root: {
    flex: "1",
    minHeight: "0",
    overflowY: "auto",
    padding: "20px",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  empty: { margin: "auto", color: "var(--muted)", fontSize: "15px" },
});
