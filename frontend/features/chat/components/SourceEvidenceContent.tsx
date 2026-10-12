// biome-ignore-all lint/a11y/noNoninteractiveTabindex: The table scroll region needs keyboard focus.
import * as stylex from "@stylexjs/stylex";
import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import type { ComponentProps } from "react";
import { styles } from "./SourceEvidenceContent.styles";

// Keep table relationships, but discard source styles and executable markup.
const evidenceSchema = {
  ...defaultSchema,
  tagNames: [...(defaultSchema.tagNames ?? []), "mark"],
  attributes: {
    ...defaultSchema.attributes,
    mark: ["className"],
    td: ["colSpan", "rowSpan"],
    th: ["colSpan", "rowSpan", "scope"],
  },
};

interface HastNode {
  type: string;
  value?: string;
  tagName?: string;
  properties?: Record<string, unknown>;
  children?: HastNode[];
}

function createHighlightPlugin(words: string[]) {
  const validWords = words.filter((w) => w.length > 0);
  if (!validWords.length) {
    return () => () => {};
  }
  const escaped = validWords.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const pattern = new RegExp(`(${escaped.join("|")})`, "gi");

  function transform(node: HastNode) {
    if (!node?.children) return;
    const newChildren: HastNode[] = [];
    for (const child of node.children) {
      if (child.type === "text" && child.value && pattern.test(child.value)) {
        pattern.lastIndex = 0;
        const parts = child.value.split(pattern);
        for (const part of parts) {
          if (!part) continue;
          if (validWords.some((w) => w.toLowerCase() === part.toLowerCase())) {
            newChildren.push({
              type: "element",
              tagName: "mark",
              properties: { className: ["search-highlight"] },
              children: [{ type: "text", value: part }],
            });
          } else {
            newChildren.push({ type: "text", value: part });
          }
        }
      } else {
        transform(child);
        newChildren.push(child);
      }
    }
    node.children = newChildren;
  }

  return () => (tree: HastNode) => {
    transform(tree);
  };
}

export function SourceEvidenceContent({
  content,
  highlightWords,
}: {
  content: string;
  highlightWords?: string[];
}) {
  const rehypePlugins: ComponentProps<typeof ReactMarkdown>["rehypePlugins"] = [
    rehypeRaw,
    ...(highlightWords && highlightWords.length > 0
      ? [createHighlightPlugin(highlightWords)]
      : []),
    [rehypeSanitize, evidenceSchema],
  ];

  return (
    <div
      {...{
        ...stylex.props(styles.markdown, styles.content),
        className: [
          "markdown-content source-evidence-content",
          stylex.props(styles.markdown, styles.content).className,
        ]
          .filter(Boolean)
          .join(" "),
      }}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={rehypePlugins}
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer">
              {children}
            </a>
          ),
          table: ({ children }) => (
            <section
              {...stylex.props(styles.tableScroll)}
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
