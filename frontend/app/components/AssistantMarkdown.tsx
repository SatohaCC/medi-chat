import { splitEvidenceSection } from "../lib/markdown";
import { MarkdownContent } from "./MarkdownContent";

interface AssistantMarkdownProps {
  content: string;
}

export function AssistantMarkdown({ content }: AssistantMarkdownProps) {
  const sections = splitEvidenceSection(content);

  return (
    <>
      <MarkdownContent content={sections.before} />
      {sections.evidence !== null && (
        <details className="markdown-source-accordion">
          <summary>{sections.title}</summary>
          <div className="markdown-content markdown-source-content">
            <MarkdownContent content={sections.evidence} />
          </div>
        </details>
      )}
      {sections.after && <MarkdownContent content={sections.after} />}
    </>
  );
}
