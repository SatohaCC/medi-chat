import * as stylex from "@stylexjs/stylex";
import { AlertTriangle, FileText, Pill, Users, Zap } from "lucide-react";
import type { Message } from "../model/chat";
import { MessageItem } from "./MessageItem";
import { styles } from "./MessageList.styles";

interface MessageListProps {
  messages: Message[];
  isStreaming: boolean;
  containerRef?: React.RefObject<HTMLElement | null>;
  openEvidenceIndex?: number | null;
  evidencePaneTab?: "sources" | "jev";
  onToggleEvidence?: (index: number, tab: "sources" | "jev") => void;
  onSelectSuggestion?: (query: string) => void;
}

export function MessageList({
  messages,
  isStreaming,
  containerRef,
  openEvidenceIndex = null,
  evidencePaneTab = "sources",
  onToggleEvidence,
  onSelectSuggestion,
}: MessageListProps) {
  return (
    <main ref={containerRef} {...stylex.props(styles.root)}>
      <div {...stylex.props(styles.inner)}>
        {messages.length === 0 ? (
          <div {...stylex.props(styles.welcomeContainer)}>
            <div {...stylex.props(styles.welcomeHeader)}>
              <div {...stylex.props(styles.welcomeIconWrapper)}>
                <FileText size={24} color="var(--user-bg)" strokeWidth={2.2} />
              </div>
              <h2 {...stylex.props(styles.welcomeTitle)}>添付文書 AI アシスタント</h2>
              <p {...stylex.props(styles.welcomeSubtitle)}>
                調べる薬を選び、質問を入力すると、登録済みの電子添文を根拠に回答します。
              </p>
            </div>

            <div>
              <h3>質問例</h3>
              <p>例を選ぶと質問欄に入ります。対象薬を確認して送信してください。</p>
            </div>

            <div {...stylex.props(styles.suggestionGrid)}>
              <button
                type="button"
                {...stylex.props(styles.suggestionCard)}
                onClick={() =>
                  onSelectSuggestion?.(
                    "選択した医薬品について、併用禁忌・併用注意の相手となる薬剤と注意点を教えてください",
                  )
                }
              >
                <div {...stylex.props(styles.suggestionCardHeader)}>
                  <span {...stylex.props(styles.suggestionCardIcon)}>
                    <Zap size={15} color="var(--user-bg)" strokeWidth={2.2} />
                  </span>
                  <span {...stylex.props(styles.suggestionCardTitle)}>
                    相互作用の確認
                  </span>
                </div>
                <p {...stylex.props(styles.suggestionCardDesc)}>
                  併用を避ける薬や注意が必要な薬を確認
                </p>
              </button>

              <button
                type="button"
                {...stylex.props(styles.suggestionCard)}
                onClick={() =>
                  onSelectSuggestion?.(
                    "選択した医薬品について、腎機能・肝機能が低下した患者や高齢者への投与量の注意を教えてください",
                  )
                }
              >
                <div {...stylex.props(styles.suggestionCardHeader)}>
                  <span {...stylex.props(styles.suggestionCardIcon)}>
                    <Users size={15} color="#0891b2" strokeWidth={2.2} />
                  </span>
                  <span {...stylex.props(styles.suggestionCardTitle)}>
                    特定背景患者の注意
                  </span>
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
                    "選択した医薬品の重大な副作用、その初期症状、発現時の対応を教えてください",
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
                    "選択した医薬品の用法・用量、服用するタイミング、飲み忘れたときの対応を教えてください",
                  )
                }
              >
                <div {...stylex.props(styles.suggestionCardHeader)}>
                  <span {...stylex.props(styles.suggestionCardIcon)}>
                    <Pill size={15} color="#0d8253" strokeWidth={2.2} />
                  </span>
                  <span {...stylex.props(styles.suggestionCardTitle)}>
                    用法・用量の詳細
                  </span>
                </div>
                <p {...stylex.props(styles.suggestionCardDesc)}>
                  用法及び用量と投与タイミング、飲み忘れ時の対応
                </p>
              </button>
            </div>
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
        {messages.length > 0 && (
          <div aria-hidden="true" {...stylex.props(styles.bottomSpacer)} />
        )}
      </div>
    </main>
  );
}
