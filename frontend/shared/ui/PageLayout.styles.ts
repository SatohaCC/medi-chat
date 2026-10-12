import * as stylex from "@stylexjs/stylex";
export const styles = stylex.create({
  root: {
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    maxWidth: { default: "1280px", "@media (max-width: 900px)": "768px" },
    marginBlock: "0",
    marginInline: "auto",
  },
});
