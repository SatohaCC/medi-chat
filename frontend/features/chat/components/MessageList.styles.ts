import * as stylex from "@stylexjs/stylex";
export const styles = stylex.create({
  root: {
    flex: "1",
    minHeight: "0",
    overflowY: "auto",
    paddingTop: "20px",
    paddingInline: "20px",
    paddingBottom: "20px",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  withBottomPadding: {
    paddingBottom: "70vh",
  },
  empty: { margin: "auto", color: "var(--muted)", fontSize: "15px" },
});
