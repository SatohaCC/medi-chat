"use client";

import * as stylex from "@stylexjs/stylex";
import { Check, FileText, X, Zap } from "lucide-react";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { Tabs } from "../../../../shared/component/Tabs";

import type { RetrievalStatus, SourceItem } from "../../model/chat";
import type { JevResponseData } from "../../model/jev";
import { JEV_INTENT_META } from "../../model/jevIntentMeta";
import { JevResponseInspector } from "../JevResponseInspector";
import { SourceEvidenceCard } from "../SourceEvidenceCard";
import {
  extractMedicineGroups,
  extractSectionGroups,
  SourceEvidenceSectionFilters,
} from "../SourceEvidenceSectionFilters";
import { styles } from "./SourceEvidencePanel.styles";

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
  const logicCount = sources.filter((s) => s.retrieved_by?.includes("logic")).length;
  const jevCount = sources.filter((s) => s.retrieved_by?.includes("jev")).length;
  const keywordCount = sources.filter((s) => s.retrieved_by?.includes("keyword")).length;
  const totalCount = sources.length;

  const countSummary = `毎回確認：${alwaysCount}件、質問の言葉：${logicCount}件、質問の意図：${jevCount}件、本文の語句：${keywordCount}件、全体：${totalCount}件`;

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
          警告・禁忌・重要な基本的注意は、質問内容にかかわらず記載がある場合に取得します。
          理由別の件数には同じ根拠が重複して含まれることがあります。
        </div>
      )}
      {jevResponse?.qualifying_intents && jevResponse.qualifying_intents.length > 1 && (
        <div {...stylex.props(styles.multipleNotice)}>
          <div {...stylex.props(styles.multipleTitle)}>
            <span {...stylex.props(styles.multipleTitleGroup)}>
              <Zap size={13} color="var(--user-bg)" strokeWidth={2} />
              複数の観点から検索
            </span>
          </div>
          <div>
            質問の意図として次の観点を読み取り、それぞれに対応する項目を検索しました。 （
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
          該当する記載は見つかりませんでした（0件）。質問を言い換えて再検索できます。
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
            <div {...stylex.props(styles.titleRow)}>
              <h2 {...stylex.props(styles.headerTitle)}>
                <FileText size={18} aria-hidden="true" strokeWidth={2} />
                添付文書の根拠
              </h2>
              <span {...stylex.props(styles.totalBadge)}>{totalCount}件</span>
            </div>
            <div {...stylex.props(styles.countSummary)}>
              <span>取得済み根拠</span>
              {countSummary.split("、").map((count) => (
                <span key={count} {...stylex.props(styles.countItem)}>
                  {count}
                </span>
              ))}
            </div>
            {retrievalStatus === "retrieving" && (
              <span {...stylex.props(styles.searchingBadge)}>
                <Zap size={12} strokeWidth={2} aria-hidden="true" />
                根拠を取得中...
              </span>
            )}
            {retrievalStatus === "complete" && (
              <span {...stylex.props(styles.completeBadge)}>
                <Check size={12} strokeWidth={2.5} aria-hidden="true" />
                根拠取得完了
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
              <X size={14} strokeWidth={2} aria-hidden="true" />
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
                  title: "質問意図の判定",
                  content: jevResponse ? (
                    <>
                      <p>
                        質問をどう読み取ったかを示します。回答の正しさや安全性を評価する表示ではありません。
                      </p>
                      <JevResponseInspector response={jevResponse} standalone />
                    </>
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
