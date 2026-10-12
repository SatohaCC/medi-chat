import * as stylex from "@stylexjs/stylex";
export const styles = stylex.create({
  root: {
    paddingBlock: "10px",
    paddingInline: "20px",
    borderBottomWidth: "1px",
    borderBottomStyle: "solid",
    borderBottomColor: "var(--border)",
    backgroundColor: "var(--assistant-bg)",
    display: "flex",
    flexDirection: "column",
    gap: "8px",
  },
  label: { fontSize: "12px", color: "var(--muted)", fontWeight: 500 },
  loading: { fontSize: "12px", color: "var(--muted)" },
  error: { fontSize: "12px", color: "#fca5a5" },
  products: { display: "flex", flexWrap: "wrap", gap: "8px" },
  selectionSummary: { fontSize: "12px", color: "var(--muted)" },
});
