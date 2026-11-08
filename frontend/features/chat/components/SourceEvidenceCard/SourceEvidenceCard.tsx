import * as stylex from "@stylexjs/stylex";
import { HighlightText } from "../../../../shared/component/HighlightText";
import type { SourceItem } from "../../model/chat";
import { formatRevision } from "../../model/markdown";
import { evidenceDesign } from "../../model/sourceEvidenceSpec";
import { ExpandableEvidenceContent } from "../ExpandableEvidenceContent";
import { SourceEvidenceDesign } from "../SourceEvidenceDesign";
import { styles } from "./SourceEvidenceCard.styles";

export interface SourceEvidenceCardProps {
  source: SourceItem;
  highlightWords?: string[];
  variant?: "compact" | "default";
}

export function SourceEvidenceCard({
  source,
  highlightWords,
  variant = "default",
}: SourceEvidenceCardProps) {
  const cardStyle = variant === "compact" ? styles.cardCompact : styles.cardDefault;

  return (
    <div
      {...stylex.props(styles.card, cardStyle)}
      data-evidence-card="true"
      data-unit-id={source.unit_id}
    >
      <div {...stylex.props(styles.cardHeader)}>
        <div {...stylex.props(styles.sectionTitleRow)}>
          <span {...stylex.props(styles.sectionTitle)}>
            <HighlightText
              text={`[${source.section.code}] ${source.section.title}`}
              words={highlightWords}
            />
          </span>
          <span {...stylex.props(styles.productLabel)}>{source.product_name}</span>
        </div>
        <div {...stylex.props(styles.badgeGroup)}>
          {source.retrieved_by?.map((method) => {
            const label =
              method === "always"
                ? "毎回確認"
                : method === "logic"
                  ? "質問の言葉に一致"
                  : method === "jev"
                    ? "質問意図から追加"
                    : method === "keyword"
                      ? "本文の語句から検索"
                      : method;
            return (
              <span key={method} {...stylex.props(styles.retrievalBadge)}>
                {label}
              </span>
            );
          })}
        </div>
      </div>

      <ExpandableEvidenceContent
        content={source.excerpt}
        highlightWords={highlightWords}
        alwaysExpanded={
          !source.retrieved_by?.includes("always") &&
          ["WarningEvidence", "ContraindicationEvidence"].includes(evidenceDesign(source))
        }
      >
        <SourceEvidenceDesign source={source} highlightWords={highlightWords} />

        <div {...stylex.props(styles.footer)}>
          <div {...stylex.props(styles.citationRow)}>
            <span {...stylex.props(styles.citationItem)}>
              改訂: {formatRevision(source.document_revision)}
            </span>
            <span {...stylex.props(styles.citationDot)}>·</span>
            <span {...stylex.props(styles.citationItem)}>
              YJコード:{" "}
              <HighlightText
                text={source.product_yj_codes.join(", ") || "不明"}
                words={highlightWords}
              />
            </span>
            {source.url && (
              <>
                <span {...stylex.props(styles.citationDot)}>·</span>
                <a
                  href={source.url}
                  target="_blank"
                  rel="noreferrer"
                  {...stylex.props(styles.documentLink)}
                >
                  PMDAの出典を開く ↗
                </a>
              </>
            )}
          </div>
        </div>
      </ExpandableEvidenceContent>
    </div>
  );
}
