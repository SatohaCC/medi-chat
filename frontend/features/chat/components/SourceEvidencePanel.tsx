"use client";

import * as stylex from "@stylexjs/stylex";
import { useState } from "react";

import { Disclosure } from "../../../shared/ui/Disclosure";
import type { RetrievalStatus, SourceItem } from "../model/chat";
import type { JevResponseData } from "../model/jev";
import { JEV_INTENT_META } from "./JevResponseInspector";
import { SourceEvidenceCard } from "./SourceEvidenceCard";
import {
  SourceEvidenceSectionFilters,
  extractSectionGroups,
} from "./SourceEvidenceSectionFilters";
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

  const sectionGroups = extractSectionGroups(sources);

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

          <SourceEvidenceSectionFilters
            sectionGroups={sectionGroups}
            totalCount={totalCount}
            selectedSection={selectedSection}
            onSelectSection={setSelectedSection}
            variant="dashedBorder"
          />

          {displayedSources.length === 0 && (
            <div {...stylex.props(styles.empty)}>
              該当する添付文書の根拠記載は見つかりませんでした（0件）
            </div>
          )}

          {displayedSources.map((s) => (
            <SourceEvidenceCard key={s.unit_id} source={s} variant="compact" />
          ))}
        </div>
      </Disclosure>
    </aside>
  );
}
