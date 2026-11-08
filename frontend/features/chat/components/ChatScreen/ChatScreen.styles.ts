import * as stylex from "@stylexjs/stylex";
export const styles = stylex.create({
  chatColumn: {
    flex: "1",
    minWidth: "0",
    minHeight: "0",
    display: "flex",
    flexDirection: "column",
  },
  missingAlert: {
    marginBlock: "var(--space-2)",
    marginInline: "auto",
    width: "calc(100% - 32px)",
    maxWidth: "840px",
    paddingBlock: "var(--space-2)",
    paddingInline: "var(--space-3)",
    borderRadius: "12px",
    backgroundColor: "var(--pending-bg)",
    borderWidth: "1px",
    borderStyle: "solid",
    borderColor: "var(--pending-border)",
    fontSize: "12px",
    color: "var(--pending-fg)",
    lineHeight: 1.4,
  },
});
