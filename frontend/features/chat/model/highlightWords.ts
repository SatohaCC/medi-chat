const STOP_WORDS = new Set([
  "大丈夫",
  "について",
  "ついて",
  "教えて",
  "お願い",
  "ください",
  "どう",
  "なに",
  "どれ",
  "どちら",
  "これ",
  "それ",
  "あれ",
  "とき",
  "こと",
  "もの",
  "ため",
  "場合",
  "よう",
  "です",
  "ます",
  "ある",
  "いる",
  "なる",
]);

const DOSAGE_FORM_PATTERN =
  /(?:錠|カプセル|散|細粒|シロップ|注|点滴|軟膏|クリーム|液)[0-9A-Za-z.％%]*$/;

// Pattern to extract medical terms, katakana, kanji compounds, and alphanumeric codes from Japanese sentences
const SCRIPT_CHUNKS_PATTERN =
  /(?:[A-Za-z0-9]+[\u30A1-\u30FA\u30FC\u4E00-\u9FFF]+|[\u30A1-\u30FA\u30FC\u4E00-\u9FFF]+[A-Za-z0-9]+)|[\u30A1-\u30FA\u30FC]{2,}|[\u4E00-\u9FFF]{2,}|[A-Za-z][A-Za-z0-9_-]*|[0-9]+(?:\.[0-9]+)?(?:mg|g|mL|ml|%)?/g;

/**
 * Extracts searchable keywords from a query string or user message for highlighting in evidence cards.
 * Strips token mention prefixes (@/＠), tokenizes Japanese sentences and punctuation,
 * extracts base medicine names and compounds, and sorts terms longest-first.
 */
export function extractHighlightWords(query?: string | null): string[] {
  if (!query) return [];
  const words = new Set<string>();
  const cleaned = query.replace(/[@＠]/g, " ");

  // Delimit initially by whitespace and major punctuation / brackets
  const chunks = cleaned.split(/[\s　、。！？!?,/／~〜()（）「」『』:：]+/);

  for (const chunk of chunks) {
    const trimmed = chunk.trim();
    if (trimmed.length <= 1) continue;

    // If chunk is a pure continuous token without particles (e.g. "ワルファリン" or "腎機能障害")
    if (
      /^[\u30A1-\u30FA\u30FC]{2,}$/.test(trimmed) ||
      /^[\u4E00-\u9FFF]{2,}$/.test(trimmed) ||
      /^[A-Za-z0-9_-]{2,}$/.test(trimmed)
    ) {
      if (!STOP_WORDS.has(trimmed)) {
        words.add(trimmed);
        if (DOSAGE_FORM_PATTERN.test(trimmed)) {
          const base = trimmed.replace(DOSAGE_FORM_PATTERN, "").trim();
          if (base.length > 1 && !STOP_WORDS.has(base)) {
            words.add(base);
          }
        }
      }
      continue;
    }

    // Natural language phrase with particles: extract keywords and compounds
    const matches = trimmed.match(SCRIPT_CHUNKS_PATTERN);
    if (matches) {
      for (const m of matches) {
        if (m.length > 1 && !STOP_WORDS.has(m)) {
          words.add(m);
          if (DOSAGE_FORM_PATTERN.test(m)) {
            const base = m.replace(DOSAGE_FORM_PATTERN, "").trim();
            if (base.length > 1 && !STOP_WORDS.has(base)) {
              words.add(base);
            }
          }
        }
      }
    }
  }

  // Always sort longest first to prevent shorter terms from prematurely consuming overlapping longer terms
  return Array.from(words).sort((a, b) => b.length - a.length);
}
