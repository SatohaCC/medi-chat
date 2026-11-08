import * as stylex from "@stylexjs/stylex";
export const styles = stylex.create({
  root: {
    display: "flex",
    flexDirection: "column",
    height: "100dvh",
    width: "100%",
    maxWidth: { default: "1920px", "@media (max-width: 900px)": "100%" },
    marginBlock: "0",
    marginInline: "auto",
    backgroundColor: "var(--bg)",
  },
  workspace: {
    flex: "1",
    minHeight: "0",
    display: "flex",
    flexDirection: { default: "row", "@media (max-width: 900px)": "column" },
    overflow: "hidden",
    position: "relative",
  },
});
