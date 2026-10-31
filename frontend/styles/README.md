# Spacing

The authored UI uses a 4px grid. CSS values live in `tokens.css`; StyleX consumes
these variables, while Spectrum S2 keeps its own component metrics.

| Role | Token | Value |
| --- | --- | --- |
| Icon/label or small internal gap | `--space-inline-tight` | 4px |
| Adjacent controls | `--space-inline` | 8px |
| Compact card padding | `--space-card-compact` | 12px |
| Reading card padding | `--space-card` | 16px |
| Section separation | `--space-section` | 24px |
| Page edge | `--space-page` | 16px up to 600px; 24px above |

Use `--space-1` through `--space-12` (4px through 48px) for other spacing.
Choose by grouping and purpose; do not round typography or geometry to this grid.
Zero spacing, automatic margins, `em` spacing in prose, safe-area insets, 1px
borders, focus outlines, visually hidden content and negative border compensation
are separate concerns. Touch targets stay at least 44px where already provided.

Keep the same layout context when expanding/collapsing evidence: `flow-root`
prevents child margins from collapsing differently between the two states.

## Color roles

`--bg` is the cool neutral canvas; `--card-bg`/`--assistant-bg` are white reading
surfaces. Use `--fg` for body text and `--muted` for secondary text.
`--user-bg` is the blue action/link color; `--accent-soft`, `--accent-hover`, and
`--accent-border` distinguish interactive states. Green indicates completion,
amber indicates pending/caution, and red indicates errors. Clinical evidence
section colors retain their existing meanings and always keep their text labels.
