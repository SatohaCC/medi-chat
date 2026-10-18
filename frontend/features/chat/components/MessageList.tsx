import * as stylex from "@stylexjs/stylex";
import {AlertTriangle, FileText, Lightbulb, Pill, Users, Zap} from "lucide-react";
import type {SelectedMedicineItem} from "../../medicine-selection";
import type {Message} from "../model/chat";
import {MessageItem} from "./MessageItem";
import {styles} from "./MessageList.styles";

interface MessageListProps {
  messages: Message[];
  isStreaming: boolean;
  containerRef?: React.RefObject<HTMLElement | null>;
  openEvidenceIndex?: number | null;
  evidencePaneTab?: "sources" | "jev";
  onToggleEvidence?: (index: number, tab: "sources" | "jev") => void;
  baseline?: SelectedMedicineItem[];
  onSelectSuggestion?: (query: string) => void;
}

export function MessageList({
  messages,
  isStreaming,
  containerRef,
  openEvidenceIndex = null,
  evidencePaneTab = "sources",
  onToggleEvidence,
  baseline = [],
  onSelectSuggestion,
}: MessageListProps) {
  const currentDrugName = baseline[0]?.name ?? "対象薬";

  return (
    <main
      ref={containerRef}
      {...stylex.props(styles.root, messages.length > 0 && styles.withBottomPadding)}
    >
      <div {...stylex.props(styles.inner)}>
        {messages.length === 0 ? (
          <div {...stylex.props(styles.welcomeContainer)}>
            <div {...stylex.props(styles.welcomeHeader)}>
              <div {...stylex.props(styles.welcomeIconWrapper)}>
                <FileText size={24} color="#0265dc" strokeWidth={2.2} />
              </div>
              <h2 {...stylex.props(styles.welcomeTitle)}>添付文書 AI アシスタント</h2>
              <p {...stylex.props(styles.welcomeSubtitle)}>
                PMDA公式の最新電子添文データをもとに、相互作用・禁忌・用法用量・副作用を迅速に確認できます。
              </p>
            </div>

            <div {...stylex.props(styles.suggestionGrid)}>
              <button
                type="button"
                {...stylex.props(styles.suggestionCard)}
                onClick={() =>
                  onSelectSuggestion?.(
                    `${currentDrugName}と併用禁忌および併用注意の薬剤について教えてください`,
                  )
                }
              >
                <div {...stylex.props(styles.suggestionCardHeader)}>
                  <span {...stylex.props(styles.suggestionCardIcon)}>
                    <Zap size={15} color="#0265dc" strokeWidth={2.2} />
                  </span>
                  <span {...stylex.props(styles.suggestionCardTitle)}>相互作用の確認</span>
                </div>
                <p {...stylex.props(styles.suggestionCardDesc)}>
                  {currentDrugName}との併用禁忌・注意薬および機序・危険因子
                </p>
              </button>

              <button
                type="button"
                {...stylex.props(styles.suggestionCard)}
                onClick={() =>
                  onSelectSuggestion?.(
                    `${currentDrugName}の腎機能・肝機能障害患者への投与基準や用量調節について教えてください`,
                  )
                }
              >
                <div {...stylex.props(styles.suggestionCardHeader)}>
                  <span {...stylex.props(styles.suggestionCardIcon)}>
                    <Users size={15} color="#0891b2" strokeWidth={2.2} />
                  </span>
                  <span {...stylex.props(styles.suggestionCardTitle)}>特定背景患者の注意</span>
                </div>
                <p {...stylex.props(styles.suggestionCardDesc)}>
                  腎・肝機能障害患者や高齢者に対する用量調節基準
                </p>
              </button>

              <button
                type="button"
                {...stylex.props(styles.suggestionCard)}
                onClick={() =>
                  onSelectSuggestion?.(
                    `${currentDrugName}の重大な副作用とその初期症状、発現時の処置について教えてください`,
                  )
                }
              >
                <div {...stylex.props(styles.suggestionCardHeader)}>
                  <span {...stylex.props(styles.suggestionCardIcon)}>
                    <AlertTriangle size={15} color="#d97706" strokeWidth={2.2} />
                  </span>
                  <span {...stylex.props(styles.suggestionCardTitle)}>重大な副作用</span>
                </div>
                <p {...stylex.props(styles.suggestionCardDesc)}>
                  初期症状の兆候、検査値の推移、発現時の対応方法
                </p>
              </button>

              <button
                type="button"
                {...stylex.props(styles.suggestionCard)}
                onClick={() =>
                  onSelectSuggestion?.(
                    `${currentDrugName}の用法及び用量と、服用タイミング・休薬に関する注意を教えてください`,
                  )
                }
              >
                <div {...stylex.props(styles.suggestionCardHeader)}>
                  <span {...stylex.props(styles.suggestionCardIcon)}>
                    <Pill size={15} color="#0d8253" strokeWidth={2.2} />
                  </span>
                  <span {...stylex.props(styles.suggestionCardTitle)}>用法・用量の詳細</span>
                </div>
                <p {...stylex.props(styles.suggestionCardDesc)}>
                  用法及び用量と投与タイミング、飲み忘れ時の対応
                </p>
              </button>
            </div>

              <p {...stylex.props(styles.welcomeSubtitle)}>
              <Lightbulb size={13} color="#0265dc" style={{ display: "inline", verticalAlign: "middle", marginRight: 6 }} />
              下の入力欄で <strong>@</strong> を入力すると、薬品名を選択して質問できます
            </p>
          </div>
        ) : (
          messages.map((msg, i) => (
            <MessageItem
              key={`msg-${i}`}
              message={msg}
              isStreaming={isStreaming}
              isLast={i === messages.length - 1}
              isEvidenceOpen={openEvidenceIndex === i}
              activeEvidenceTab={openEvidenceIndex === i ? evidencePaneTab : undefined}
              onToggleEvidence={
                onToggleEvidence
                  ? (tab: "sources" | "jev") => onToggleEvidence(i, tab)
                  : undefined
              }
            />
          ))
        )}
      </div>
    </main>
  );
}
