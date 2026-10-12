import type { SourceItem } from "./chat";

export function formatRevision(revision: SourceItem["document_revision"]): string {
  return (
    [revision.source_label, revision.year_month, revision.version]
      .filter(Boolean)
      .join(" / ") || "不明"
  );
}

export interface EvidenceSectionResult {
  before: string;
  evidence: string | null;
  after: string;
  title: string | null;
}

export function splitEvidenceSection(markdown: string): EvidenceSectionResult {
  const lines = markdown.split(/\r?\n/);
  const headingPattern = /^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$/;
  const evidenceHeadings = ["根拠・改訂情報・出典", "根拠・出典"];
  const start = lines.findIndex((line) => {
    const match = line.match(headingPattern);
    return evidenceHeadings.includes(match?.[2].replace(/[*_`]/g, "").trim() ?? "");
  });

  if (start === -1) {
    return { before: markdown, evidence: null, after: "", title: null };
  }

  const match = lines[start].match(headingPattern);
  if (!match) {
    return { before: markdown, evidence: null, after: "", title: null };
  }
  const title = match[2].replace(/[*_`]/g, "").trim();
  const level = match[1].length;
  let end = lines.length;

  for (let index = start + 1; index < lines.length; index += 1) {
    const nextHeading = lines[index].match(headingPattern);
    if (nextHeading && nextHeading[1].length <= level) {
      end = index;
      break;
    }
  }

  const before = lines.slice(0, start).join("\n").trim();
  const evidence = lines
    .slice(start + 1, end)
    .join("\n")
    .trim();
  const after = lines.slice(end).join("\n").trim();
  return { before, evidence, after, title };
}
