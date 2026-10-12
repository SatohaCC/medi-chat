import * as stylex from "@stylexjs/stylex";
import { Disclosure } from "../../../shared/ui/Disclosure";
import { splitEvidenceSection } from "../model/markdown";
import { styles } from "./AssistantMarkdown.styles";
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
        <Disclosure variant="markdown" title={sections.title}>
          <div
            {...{
              ...stylex.props(styles.markdown, styles.evidence),
              className: [
                "markdown-content",
                stylex.props(styles.markdown, styles.evidence).className,
              ]
                .filter(Boolean)
                .join(" "),
            }}
          >
            <MarkdownContent content={sections.evidence} />
          </div>
        </Disclosure>
      )}
      {sections.after && <MarkdownContent content={sections.after} />}
    </>
  );
}
