import type { ReactNode } from "react";

export function HighlightText({
  text,
  words,
}: {
  text: string;
  words?: string[];
}): ReactNode {
  if (!text || !words || words.length === 0) return text;
  const validWords = words.filter((w) => w.length > 0);
  if (!validWords.length) return text;
  const escaped = validWords.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const pattern = new RegExp(`(${escaped.join("|")})`, "gi");
  const parts = text.split(pattern);
  return (
    <>
      {parts.map((part, index) => {
        if (!part) return null;
        const isMatch = validWords.some((w) => w.toLowerCase() === part.toLowerCase());
        return isMatch ? (
          <mark key={`${part}-${index}`} className="search-highlight">
            {part}
          </mark>
        ) : (
          part
        );
      })}
    </>
  );
}
