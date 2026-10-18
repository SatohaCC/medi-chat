"use client";

import * as stylex from "@stylexjs/stylex";
import { useState } from "react";

import type { RetrievalStatus, SourceItem } from "../model/chat";
import type { JevResponseData } from "../model/jev";
import { JEV_INTENT_META, JevResponseInspector } from "./JevResponseInspector";
import { SourceEvidenceCard } from "./SourceEvidenceCard";
import { styles } from "./SourceEvidencePanel.styles";
import {
  extractSectionGroups,
  SourceEvidenceSectionFilters,
} from "./SourceEvidenceSectionFilters";

interface SourceEvidencePanelProps {
  sources: SourceItem[];
  retrievalStatus?: RetrievalStatus;
  jevResponse?: JevResponseData | null;
  activeTab?: "sources" | "jev";
  onTabChange?: (tab: "sources" | "jev") => void;
  onClose?: () => void;
}

export function SourceEvidencePanel({
  sources,
  retrievalStatus,
  jevResponse,
  activeTab = "sources",
  onTabChange,
  onClose,
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

  const hasJev = Boolean(jevResponse);
  const currentTab = hasJev ? activeTab : "sources";

  return (
    <aside {...stylex.props(styles.panel)} aria-label="添付文書の根拠引用">
      <div {...stylex.props(styles.headerBar)}>
        {hasJev ? (
          <div {...stylex.props(styles.tabGroup)} role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={currentTab === "sources"}
              onClick={() => onTabChange?.("sources")}
              {...stylex.props(
                styles.tabButton,
                currentTab === "sources" && styles.tabButtonActiveSources,
              )}
            >
              📄 添付文書の根拠 ({totalCount}件)
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={currentTab === "jev"}
              onClick={() => onTabChange?.("jev")}
              {...stylex.props(
                styles.tabButton,
                currentTab === "jev" && styles.tabButtonActiveJev,
              )}
            >
              ⚡ Jev判定インスペクター
            </button>
          </div>
        ) : (
          <div {...stylex.props(styles.headerTitleGroup)}>
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
          </div>
        )}

        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="根拠パネルを閉じる"
            {...stylex.props(styles.closeButton)}
          >
            ✕ 閉じる
          </button>
        )}
      </div>

      <div {...stylex.props(styles.content)}>
        {currentTab === "jev" && jevResponse && (
          <JevResponseInspector response={jevResponse} standalone />
        )}

        {currentTab === "sources" && (
          <>
            {jevResponse?.qualifying_intents && jevResponse.qualifying_intents.length > 1 && (
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
          </>
        )}
      </div>
    </aside>
  );
}
