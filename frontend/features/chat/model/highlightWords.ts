/**
 * Extracts searchable keywords from a query string or user message for highlighting in evidence cards.
 * Strips token mention prefixes (@/＠), splits by whitespace and common punctuation,
 * and keeps unique words longer than 1 character.
 */
export function extractHighlightWords(query?: string | null): string[] {
  if (!query) return [];
  const rawWords = query
    .replace(/[@＠]/g, " ")
    .split(/[\s　、。！？!?,/／]+/)
    .map((w) => w.trim())
    .filter(Boolean)
    .filter((w) => w.length > 1);

  return Array.from(new Set(rawWords));
}
