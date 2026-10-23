"use client";

import * as stylex from "@stylexjs/stylex";
import { Check, FileText, X, Zap } from "lucide-react";
import { useState } from "react";

import type { RetrievalStatus, SourceItem } from "../model/chat";
import type { JevResponseData } from "../model/jev";
import { JEV_INTENT_META, JevResponseInspector } from "./JevResponseInspector";
import { SourceEvidenceCard } from "./SourceEvidenceCard";
import { styles } from "./SourceEvidencePanel.styles";
import {
  extractMedicineGroups,
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
  highlightWords?: string[];
}

export function SourceEvidencePanel({
  sources,
  retrievalStatus,
  jevResponse,
  activeTab = "sources",
  onTabChange,
  onClose,
  highlightWords,
}: SourceEvidencePanelProps) {
  const [selectedSection, setSelectedSection] = useState<string>("all");
  const [selectedMedicine, setSelectedMedicine] = useState<string>("all");

  const alwaysCount = sources.filter((s) => s.retrieved_by?.includes("always")).length;
  const alwaysSummary = alwaysCount > 0 ? `常時取得：${alwaysCount}件、` : "";
  const logicCount = sources.filter((s) => s.retrieved_by?.includes("logic")).length;
  const jevCount = sources.filter((s) => s.retrieved_by?.includes("jev")).length;
  const keywordCount = sources.filter((s) => s.retrieved_by?.includes("keyword")).length;
  const totalCount = sources.length;

  const countSummary =
    keywordCount > 0
      ? `${alwaysSummary}ロジック：${logicCount}件、Jev：${jevCount}件、キーワード：${keywordCount}件、合計：${totalCount}件`
      : `${alwaysSummary}ロジック：${logicCount}件、Jev：${jevCount}件、合計：${totalCount}件`;

  const sectionGroups = extractSectionGroups(sources);
  const medicineGroups = extractMedicineGroups(sources);

  const displayedSources = sources.filter((s) => {
    const matchesSection =
      selectedSection === "all" || (s.section?.code || "other") === selectedSection;
    const drugName = s.product_name || s.generic_name || "その他";
    const matchesMedicine = selectedMedicine === "all" || drugName === selectedMedicine;
    return matchesSection && matchesMedicine;
  });

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
              <FileText size={13} strokeWidth={2} />
              <span>添付文書の根拠 ({totalCount}件)</span>
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
              <Zap size={13} strokeWidth={2} />
              <span>Jev判定インスペクター</span>
            </button>
          </div>
        ) : (
          <div {...stylex.props(styles.headerTitleGroup)}>
            <span {...stylex.props(styles.headerTitle)}>
              <FileText size={14} color="#0265dc" strokeWidth={2} />
              {retrievalStatus === "complete"
                ? `統合根拠（${countSummary}）`
                : retrievalStatus === "jev_searching"
                  ? `取得済み根拠（${alwaysSummary}ロジック：${logicCount}件、キーワード：${keywordCount}件、合計：${totalCount}件、Jev：取得中...）`
                  : `取得済み根拠（${countSummary}）`}
            </span>
            {retrievalStatus === "jev_searching" && (
              <span {...stylex.props(styles.searchingBadge)}>
                <Zap size={12} strokeWidth={2} />
                Jev判定と統合中...
              </span>
            )}
            {retrievalStatus === "complete" && (
              <span {...stylex.props(styles.completeBadge)}>
                <Check size={12} strokeWidth={2.5} />
                Jev統合完了
              </span>
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
            <X size={13} strokeWidth={2} />
            <span>閉じる</span>
          </button>
        )}
      </div>

      <div {...stylex.props(styles.content)}>
        {currentTab === "jev" && jevResponse && (
          <JevResponseInspector response={jevResponse} standalone />
        )}

        {currentTab === "sources" && (
          <>
            {alwaysCount > 0 && (
              <div {...stylex.props(styles.multipleNotice)}>
                警告・禁忌・重要な基本的注意は、質問内容にかかわらず、記載がある場合に取得します。
                {countSummary}
                。取得理由別の件数には重複が含まれ、合計は重複を除いた件数です。
              </div>
            )}
            {jevResponse?.qualifying_intents &&
              jevResponse.qualifying_intents.length > 1 && (
                <div {...stylex.props(styles.multipleNotice)}>
                  <div {...stylex.props(styles.multipleTitle)}>
                    <span {...stylex.props(styles.multipleTitleGroup)}>
                      <Zap size={13} color="#0265dc" strokeWidth={2} />
                      マルチセクション取得（閾値20%以上）
                    </span>
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
              medicineGroups={medicineGroups}
              selectedMedicine={selectedMedicine}
              onSelectMedicine={setSelectedMedicine}
              variant="dashedBorder"
            />

            {displayedSources.length === 0 && (
              <div {...stylex.props(styles.empty)}>
                該当する添付文書の根拠記載は見つかりませんでした（0件）
              </div>
            )}

            {displayedSources.map((s) => (
              <SourceEvidenceCard
                key={s.unit_id}
                source={s}
                variant="compact"
                highlightWords={highlightWords}
              />
            ))}
          </>
        )}
      </div>
    </aside>
  );
}
