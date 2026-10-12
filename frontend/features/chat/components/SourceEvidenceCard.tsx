import * as stylex from "@stylexjs/stylex";
import type { SourceItem } from "../model/chat";
import { formatRevision } from "../model/markdown";
import { HighlightText } from "./HighlightText";
import { styles } from "./SourceEvidenceCard.styles";
import { SourceEvidenceContent } from "./SourceEvidenceContent";

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
    <div {...stylex.props(styles.card, cardStyle)} data-evidence-card="true">
      <div {...stylex.props(styles.cardHeader)}>
        <div {...stylex.props(styles.sectionTitleRow)}>
          <span {...stylex.props(styles.sectionTitle)}>
            <HighlightText
              text={`[${source.section.code}] ${source.section.title}`}
              words={highlightWords}
            />
          </span>
          <span {...stylex.props(styles.productLabel)}>
            <HighlightText text={source.product_name} words={highlightWords} />
          </span>
        </div>
        <div>
          {source.retrieved_by?.map((method) => {
            const label =
              method === "logic"
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

      {source.columns ? (
        <div {...stylex.props(styles.metadata)}>
          {source.columns.drug_name && (
            <div>
              <span {...stylex.props(styles.metaLabel)}>併用薬: </span>
              <span>
                <HighlightText text={source.columns.drug_name} words={highlightWords} />
              </span>
            </div>
          )}
          {source.columns.clinical_symptoms_and_measures && (
            <div>
              <span {...stylex.props(styles.metaLabel)}>臨床症状・措置: </span>
              <span>
                <HighlightText
                  text={source.columns.clinical_symptoms_and_measures}
                  words={highlightWords}
                />
              </span>
            </div>
          )}
          {source.columns.mechanism_and_risk_factors && (
            <div>
              <span {...stylex.props(styles.metaLabel)}>機序・危険因子: </span>
              <span>
                <HighlightText
                  text={source.columns.mechanism_and_risk_factors}
                  words={highlightWords}
                />
              </span>
            </div>
          )}
        </div>
      ) : (
        <SourceEvidenceContent content={source.excerpt} highlightWords={highlightWords} />
      )}

      <div {...stylex.props(styles.footer)}>
        <div>改訂: {formatRevision(source.document_revision)}</div>
        <div>
          YJコード:{" "}
          <HighlightText
            text={source.product_yj_codes.join(", ") || "不明"}
            words={highlightWords}
          />
        </div>
        {source.url && (
          <a
            href={source.url}
            target="_blank"
            rel="noreferrer"
            {...stylex.props(styles.documentLink)}
          >
            PMDAの出典を開く
          </a>
        )}
        {source.references && source.references.length > 0 && (
          <div>
            参照先:{" "}
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
      <div {...stylex.props(styles.unitId)}>単位ID: {source.unit_id}</div>
    </div>
  );
}
