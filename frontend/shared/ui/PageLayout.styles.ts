import * as stylex from "@stylexjs/stylex";
export const styles = stylex.create({
  root: {
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    width: "100%",
    maxWidth: { default: "1920px", "@media (max-width: 900px)": "100%" },
    marginBlock: "0",
    marginInline: "auto",
  },
});
