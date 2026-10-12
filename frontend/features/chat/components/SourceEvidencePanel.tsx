"use client";

import * as stylex from "@stylexjs/stylex";
import { useState } from "react";

import { Button } from "../../../shared/ui/Button";
import { Disclosure } from "../../../shared/ui/Disclosure";
import type { RetrievalStatus, SourceItem } from "../model/chat";
import type { JevResponseData } from "../model/jev";
import { formatRevision } from "../model/markdown";
import { JEV_INTENT_META } from "./JevResponseInspector";
import { SourceEvidenceContent } from "./SourceEvidenceContent";
import { styles } from "./SourceEvidencePanel.styles";

interface SourceEvidencePanelProps {
  sources: SourceItem[];
  retrievalStatus?: RetrievalStatus;
  jevResponse?: JevResponseData | null;
}

export function SourceEvidencePanel({
  sources,
  retrievalStatus,
  jevResponse,
}: SourceEvidencePanelProps) {
  const [selectedSection, setSelectedSection] = useState<string>("all");

  const logicCount = sources.filter((s) => s.retrieved_by?.includes("logic")).length;
  const jevCount = sources.filter((s) => s.retrieved_by?.includes("jev")).length;
  const keywordCount = sources.filter((s) => s.retrieved_by?.includes("keyword")).length;
  const totalCount = sources.length;

  const countSummary =
    keywordCount > 0
      ? `ロジック：${logicCount}件、Jev：${jevCount}件、キーワード：${keywordCount}件、合計：${totalCount}件`
      : `ロジック：${logicCount}件、Jev：${jevCount}件、合計：${totalCount}件`;

  // Extract unique sections in original sorted order
  const sectionCodesInOrder: string[] = [];
  const sectionMap = new Map<string, { code: string; title: string; count: number }>();
  for (const s of sources) {
    const code = s.section?.code || "other";
    const title = s.section?.title || "";
    const existing = sectionMap.get(code);
    if (existing) {
      existing.count += 1;
    } else {
      sectionCodesInOrder.push(code);
      sectionMap.set(code, { code, title, count: 1 });
    }
  }
  const sectionGroups = sectionCodesInOrder
    .map((code) => sectionMap.get(code))
    .filter((g): g is { code: string; title: string; count: number } => g !== undefined);

  const displayedSources =
    selectedSection === "all"
      ? sources
      : sources.filter((s) => (s.section?.code || "other") === selectedSection);

  return (
    <aside {...stylex.props(styles.panel)} aria-label="添付文書の根拠引用">
      <Disclosure
        variant="source"
        defaultOpen
        title={
          <>
            <span>
              📄{" "}
              {retrievalStatus === "complete"
                ? `統合根拠（${countSummary}）`
                : retrievalStatus === "jev_searching"
                  ? `ロジック検索根拠（ロジック：${totalCount}件、Jev：取得中...）`
                  : `ロジック検索根拠（${totalCount}件）`}
            </span>
            {retrievalStatus === "jev_searching" && (
              <span {...stylex.props(styles.searchingBadge)}>⚡ Jev判定と統合中...</span>
            )}
            {retrievalStatus === "complete" && (
              <span {...stylex.props(styles.completeBadge)}>✓ Jev統合完了</span>
            )}
            {jevResponse?.answers?.intent?.choice && (
              <span
                {...stylex.props(
                  styles.intentBadge(
                    jevResponse.qualifying_intents &&
                      jevResponse.qualifying_intents.length > 1
                      ? "#67e8f9"
                      : "#c084fc",
                    jevResponse.qualifying_intents &&
                      jevResponse.qualifying_intents.length > 1
                      ? "rgba(6, 182, 212, 0.15)"
                      : "rgba(168, 85, 247, 0.15)",
                    jevResponse.qualifying_intents &&
                      jevResponse.qualifying_intents.length > 1
                      ? "rgba(6, 182, 212, 0.35)"
                      : "rgba(168, 85, 247, 0.3)",
                  ),
                )}
              >
                ⚡ Jev:{" "}
                {jevResponse.qualifying_intents &&
                jevResponse.qualifying_intents.length > 1
                  ? `マルチ (${jevResponse.qualifying_intents
                      .map((k) => JEV_INTENT_META[k]?.label || k)
                      .join(" + ")})`
                  : `${
                      JEV_INTENT_META[jevResponse.answers.intent.choice]?.label ||
                      jevResponse.answers.intent.choice
                    }${
                      jevResponse.answers.intent.confidence !== undefined
                        ? ` (${Math.round(jevResponse.answers.intent.confidence * 100)}%)`
                        : ""
                    }`}
              </span>
            )}
          </>
        }
      >
        <div {...stylex.props(styles.content)}>
          {jevResponse?.qualifying_intents &&
            jevResponse.qualifying_intents.length > 1 && (
              <div {...stylex.props(styles.multipleNotice)}>
                <div {...stylex.props(styles.multipleTitle)}>
                  <span>⚡ マルチセクション取得（閾値20%以上）</span>
                </div>
                <div>
                  確率20%以上の全候補項目（
                  {jevResponse.qualifying_intents
                    .map((k) => JEV_INTENT_META[k]?.label || k)
                    .join("・")}
                  ）のセクションを網羅して取得し、LLMに提供しています。
                </div>
              </div>
            )}

          {sectionGroups.length > 1 && (
            <div {...stylex.props(styles.sectionFilters)}>
              <span {...stylex.props(styles.filterLabel)}>セクション別:</span>
              <Button
                variant="filterAll"
                selected={selectedSection === "all"}
                onActivate={() => setSelectedSection("all")}
              >
                すべて ({totalCount})
              </Button>
              {sectionGroups.map((g) => {
                const isSelected = selectedSection === g.code;
                return (
                  <Button
                    key={g.code}
                    variant="filterSection"
                    selected={isSelected}
                    onActivate={() => setSelectedSection(isSelected ? "all" : g.code)}
                  >
                    [{g.code}] {g.title} ({g.count})
                  </Button>
                );
              })}
            </div>
          )}

          {displayedSources.length === 0 && (
            <div {...stylex.props(styles.empty)}>
              該当する添付文書の根拠記載は見つかりませんでした（0件）
            </div>
          )}

          {displayedSources.map((s) => (
            <div
              key={s.unit_id}
              {...stylex.props(styles.card, styles.cardPresentation)}
              data-evidence-card="true"
            >
              <div {...stylex.props(styles.cardHeader)}>
                <div {...stylex.props(styles.sectionTitleRow)}>
                  <span {...stylex.props(styles.sectionTitle)}>
                    [{s.section.code}] {s.section.title}
                  </span>
                  <span {...stylex.props(styles.productLabel)}>{s.product_name}</span>
                </div>
                <div>
                  {s.retrieved_by.map((source) => (
                    <span key={source} {...stylex.props(styles.retrievalBadge)}>
                      {
                        {
                          logic: "ロジック取得",
                          jev: "Jev判定取得",
                          keyword: "形態素キーワード",
                        }[source]
                      }
                    </span>
                  ))}
                </div>
              </div>
              {s.columns ? (
                <div {...stylex.props(styles.metadata)}>
                  {s.columns.drug_name && (
                    <div>
                      <span {...stylex.props(styles.logicLabel)}>併用薬: </span>
                      <span>{s.columns.drug_name}</span>
                    </div>
                  )}
                  {s.columns.clinical_symptoms_and_measures && (
                    <div>
                      <span {...stylex.props(styles.jevLabel)}>臨床症状・措置: </span>
                      <span>{s.columns.clinical_symptoms_and_measures}</span>
                    </div>
                  )}
                  {s.columns.mechanism_and_risk_factors && (
                    <div>
                      <span {...stylex.props(styles.keywordLabel)}>機序・危険因子: </span>
                      <span>{s.columns.mechanism_and_risk_factors}</span>
                    </div>
                  )}
                </div>
              ) : (
                <SourceEvidenceContent content={s.excerpt} />
              )}
              <div {...stylex.props(styles.footer)}>
                <div>改訂: {formatRevision(s.document_revision)}</div>
                <div>YJコード: {s.product_yj_codes.join(", ") || "不明"}</div>
                {s.url && (
                  <a
                    href={s.url}
                    target="_blank"
                    rel="noreferrer"
                    {...stylex.props(styles.documentLink)}
                  >
                    PMDAの出典を開く
                  </a>
                )}
                {s.references.length > 0 && (
                  <div>
                    参照先:{" "}
                    {s.references.map((reference, referenceIndex) => {
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
                          {referenceIndex < s.references.length - 1 ? ", " : ""}
                        </span>
                      );
                    })}
                  </div>
                )}
              </div>
              <div {...stylex.props(styles.unitId)}>単位ID: {s.unit_id}</div>
            </div>
          ))}
        </div>
      </Disclosure>
    </aside>
  );
}
