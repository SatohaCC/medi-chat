import * as stylex from "@stylexjs/stylex";
export const styles = stylex.create({
  controls: { display: "flex", alignItems: "center", gap: "12px" },
  headingRow: { display: "flex", alignItems: "center", gap: "12px" },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    paddingBlock: "16px",
    paddingInline: "20px",
    borderBottomWidth: "1px",
    borderBottomStyle: "solid",
    borderBottomColor: "var(--border)",
    backgroundColor: "var(--assistant-bg)",
  },
  title: { fontSize: "18px", fontWeight: 600 },
  status: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    fontSize: "13px",
    color: "var(--muted)",
    textTransform: "capitalize",
  },
  dot: {
    width: "8px",
    height: "8px",
    borderRadius: "50%",
    backgroundColor: "var(--muted)",
  },
  connectedDot: { backgroundColor: "#22c55e" },
  connectingDot: { backgroundColor: "#eab308" },
  disconnectedDot: { backgroundColor: "var(--error)" },
});
