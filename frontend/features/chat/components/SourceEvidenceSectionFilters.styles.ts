import * as stylex from "@stylexjs/stylex";

export const styles = stylex.create({
  filterContainer: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
    paddingBlock: "6px",
    paddingInline: "0",
  },
  filterRow: {
    display: "flex",
    flexWrap: "wrap",
    alignItems: "center",
    gap: "6px",
  },
  dashedBorder: {
    borderBottomWidth: "1px",
    borderBottomStyle: "dashed",
    borderBottomColor: "var(--border)",
    paddingBottom: "8px",
  },
  filterLabel: {
    fontSize: "11px",
    color: "var(--muted)",
    alignSelf: "center",
    marginRight: "2px",
    fontWeight: 500,
  },
});
