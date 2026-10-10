// biome-ignore-all lint/a11y/noNoninteractiveTabindex: The table scroll region needs keyboard focus.
import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import remarkGfm from "remark-gfm";

// Keep table relationships, but discard source styles and executable markup.
const evidenceSchema = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    td: ["colSpan", "rowSpan"],
    th: ["colSpan", "rowSpan", "scope"],
  },
};

export function SourceEvidenceContent({ content }: { content: string }) {
  return (
    <div className="markdown-content source-evidence-content">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw, [rehypeSanitize, evidenceSchema]]}
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer">
              {children}
            </a>
          ),
          table: ({ children }) => (
            <section
              className="source-table-scroll"
              tabIndex={0}
              aria-label="添付文書の表（横スクロール）"
            >
              <table>{children}</table>
            </section>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
