import * as stylex from "@stylexjs/stylex";
import type { SourceItem } from "../model/chat";
import { formatRevision } from "../model/markdown";
import { evidenceDesign } from "../model/sourceEvidenceSpec";
import { ExpandableEvidenceContent } from "./ExpandableEvidenceContent";
import { HighlightText } from "./HighlightText";
import { styles } from "./SourceEvidenceCard.styles";
import { SourceEvidenceDesign } from "./SourceEvidenceDesign";

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
                ? "常時取得"
                : method === "logic"
                  ? "ロジック取得"
                  : method === "jev"
                    ? "Jev判定取得"
                    : method === "keyword"
                      ? "形態素キーワード"
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
          {source.references && source.references.length > 0 && (
            <div {...stylex.props(styles.referenceRow)}>
              <span>参照先: </span>
              {source.references.map((reference, referenceIndex) => {
                const label = [
                  reference.kind,
                  reference.target_section_code
                    ? `項目 ${reference.target_section_code}`
                    : null,
                ]
                  .filter(Boolean)
                  .join(" / ");
                return (
                  <span key={`${label}-${referenceIndex}`}>
                    {reference.target_url ? (
                      <a
                        href={reference.target_url}
                        target="_blank"
                        rel="noreferrer"
                        {...stylex.props(styles.referenceLink)}
                      >
                        {label || reference.target_url}
                      </a>
                    ) : (
                      label || "参照"
                    )}
                    {referenceIndex < source.references.length - 1 ? ", " : ""}
                  </span>
                );
              })}
            </div>
          )}
        </div>
      </ExpandableEvidenceContent>
    </div>
  );
}
