import * as stylex from "@stylexjs/stylex";
export const styles = stylex.create({
  controls: { display: "flex", alignItems: "center", gap: "var(--space-3)" },
  headingRow: { display: "flex", alignItems: "center", gap: "var(--space-3)" },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    paddingBlock: "var(--space-4)",
    paddingInline: "var(--space-5)",
    borderBottomWidth: "1px",
    borderBottomStyle: "solid",
    borderBottomColor: "var(--border)",
    backgroundColor: "var(--assistant-bg)",
  },
  title: { fontSize: "18px", fontWeight: 600 },
});
