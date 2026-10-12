import * as stylex from "@stylexjs/stylex";

export const styles = stylex.create({
  sectionFilters: {
    display: "flex",
    flexWrap: "wrap",
    gap: "6px",
    paddingBlock: "6px",
    paddingInline: "0",
  },
  dashedBorder: {
    borderBottomWidth: "1px",
    borderBottomStyle: "dashed",
    borderBottomColor: "var(--border)",
    gap: "4px",
  },
  filterLabel: {
    fontSize: "11px",
    color: "var(--muted)",
    alignSelf: "center",
    marginRight: "2px",
  },
});
