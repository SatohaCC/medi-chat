"use client";

import * as stylex from "@stylexjs/stylex";
import { Check, FileText, X, Zap } from "lucide-react";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { Tabs } from "../../../shared/ui/Tabs";

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
  isMobile?: boolean;
  sources: SourceItem[];
  retrievalStatus?: RetrievalStatus;
  jevResponse?: JevResponseData | null;
  activeTab?: "sources" | "jev";
  onTabChange?: (tab: "sources" | "jev") => void;
  onClose?: () => void;
  highlightWords?: string[];
}

export function SourceEvidencePanel({
  isMobile = false,
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
  const sourceContent = (
    <div {...stylex.props(styles.sourceList)}>
      {alwaysCount > 0 && (
        <div {...stylex.props(styles.multipleNotice)}>
          警告・禁忌・重要な基本的注意は、質問内容にかかわらず、記載がある場合に取得します。
          {countSummary}
          。取得理由別の件数には重複が含まれ、合計は重複を除いた件数です。
        </div>
      )}
      {jevResponse?.qualifying_intents && jevResponse.qualifying_intents.length > 1 && (
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
    </div>
  );

  const panel = (
    <aside {...stylex.props(styles.panel)} aria-label="添付文書の根拠引用">
      <div {...stylex.props(styles.panelInner)}>
        <div {...stylex.props(styles.headerBar)}>
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
          {hasJev ? (
            <Tabs
              value={currentTab}
              onValueChange={(tab) => onTabChange?.(tab as "sources" | "jev")}
              label="根拠パネル表示切替"
              items={[
                { id: "sources", title: "添付文書の根拠", content: sourceContent },
                {
                  id: "jev",
                  title: "Jev判定インスペクター",
                  content: jevResponse ? (
                    <JevResponseInspector response={jevResponse} standalone />
                  ) : null,
                },
              ]}
            />
          ) : (
            sourceContent
          )}
        </div>
      </div>
    </aside>
  );
  return isMobile ? (
    <MobileEvidenceDialog onClose={onClose}>{panel}</MobileEvidenceDialog>
  ) : (
    panel
  );
}

function MobileEvidenceDialog({
  children,
  onClose,
}: {
  children: ReactNode;
  onClose?: () => void;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    const returnFocusTo = document.activeElement;
    dialog.showModal();
    return () => {
      dialog.close();
      queueMicrotask(() => {
        if (returnFocusTo instanceof HTMLElement && returnFocusTo.isConnected) {
          returnFocusTo.focus();
        }
      });
    };
  }, []);

  return (
    <dialog
      ref={dialogRef}
      aria-label="添付文書の根拠"
      {...stylex.props(styles.mobileDialog)}
      onCancel={(event) => {
        event.preventDefault();
        onClose?.();
      }}
    >
      {children}
    </dialog>
  );
}
