import * as stylex from "@stylexjs/stylex";

export const styles = stylex.create({
  filterContainer: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-inline)",
    paddingBlock: "var(--space-2)",
    paddingInline: "0",
  },
  filterRow: {
    display: "flex",
    flexWrap: "wrap",
    alignItems: "center",
    gap: "var(--space-inline)",
  },
  dashedBorder: {
    borderBottomWidth: "1px",
    borderBottomStyle: "solid",
    borderBottomColor: "var(--border)",
    paddingBottom: "var(--space-4)",
  },
  filterLabel: {
    fontSize: "12px",
    color: "var(--muted)",
    alignSelf: "center",
    marginRight: "var(--space-1)",
    fontWeight: 600,
  },
});
