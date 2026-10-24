import * as stylex from "@stylexjs/stylex";

export const styles = stylex.create({
  main: {
    display: "flex",
    justifyContent: "center",
    paddingBlock: "32px",
    paddingInline: "24px",
  },
  section: {
    width: "100%",
    maxWidth: "400px",
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  },
});
