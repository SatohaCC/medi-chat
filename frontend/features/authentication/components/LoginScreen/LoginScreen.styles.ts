import * as stylex from "@stylexjs/stylex";

export const styles = stylex.create({
  main: {
    display: "flex",
    justifyContent: "center",
    paddingBlock: "var(--space-8)",
    paddingInline: "var(--space-page)",
  },
  section: {
    width: "100%",
    maxWidth: "400px",
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-4)",
  },
});
