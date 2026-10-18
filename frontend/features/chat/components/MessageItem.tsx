import * as stylex from "@stylexjs/stylex";
import type { Message } from "../model/chat";
import { AssistantMarkdown } from "./AssistantMarkdown";
import { JEV_INTENT_META } from "./JevResponseInspector";
import { styles } from "./MessageItem.styles";

interface MessageItemProps {
  message: Message;
  isStreaming: boolean;
  isLast: boolean;
  isEvidenceOpen?: boolean;
  activeEvidenceTab?: "sources" | "jev";
  onToggleEvidence?: (tab: "sources" | "jev") => void;
}

export function MessageItem({
  message,
  isStreaming,
  isLast,
  isEvidenceOpen = false,
  activeEvidenceTab = "sources",
  onToggleEvidence,
}: MessageItemProps) {
  const hasSources =
    (Array.isArray(message.sources) && message.sources.length > 0) ||
    message.retrievalStatus === "complete" ||
    message.retrievalStatus === "jev_searching";
  const hasJev = Boolean(message.jevResponse);
  const hasEvidence =
    message.role === "assistant" && (hasSources || hasJev);

  return (
    <div
      {...stylex.props(styles.message, message.role === "user" && styles.user)}
      data-message-role={message.role}
      data-message-error={message.isError ? "true" : "false"}
    >
      <div
        {...stylex.props(
          styles.bubble,
          message.role === "user" ? styles.userBubble : styles.assistantBubble,
          message.isError && styles.errorBubble,
          hasEvidence && styles.evidenceBubble,
        )}
        data-message-bubble="true"
      >
        {message.role === "assistant" ? (
          <div
            {...{
              ...stylex.props(styles.markdown),
              className: ["markdown-content", stylex.props(styles.markdown).className]
                .filter(Boolean)
                .join(" "),
            }}
          >
            <AssistantMarkdown content={message.content} />
          </div>
        ) : (
          <div {...stylex.props(styles.userText)}>{message.content}</div>
        )}

        {message.role === "assistant" &&
          message.notices &&
          message.notices.length > 0 && (
            <div {...stylex.props(styles.noticeBox)} role="note">
              {message.notices.map((notice, index) => (
                <div key={index} {...stylex.props(styles.noticeRow)}>
                  <span {...stylex.props(styles.noticeIcon)}>⚠️</span>
                  <span>{notice}</span>
                </div>
              ))}
            </div>
          )}

        {message.retrievalStatus && (
          <div role="status" {...stylex.props(styles.statusText)}>
            {message.retrievalStatus === "jev_searching" && "Jevで根拠を検索中…"}
            {message.retrievalStatus === "complete" && "Jev検索完了"}
            {message.retrievalStatus === "unavailable" && "Jev未接続（ロジック検索のみ）"}
          </div>
        )}

        {message.isInterrupted && message.role === "assistant" && (
          <div role="status" {...stylex.props(styles.statusText)}>
            通信が切断され、回答が中断されました。未完了の回答です。
          </div>
        )}

        {hasEvidence && onToggleEvidence && (
          <div {...stylex.props(styles.evidenceActionRow)}>
            {hasSources && (
              <button
                type="button"
                onClick={() => onToggleEvidence("sources")}
                aria-pressed={isEvidenceOpen && activeEvidenceTab === "sources"}
                data-evidence-toggle="true"
                {...stylex.props(
                  styles.evidenceToggleButton,
                  isEvidenceOpen &&
                    activeEvidenceTab === "sources" &&
                    styles.evidenceToggleButtonActive,
                )}
              >
                <span>
                  📄{" "}
                  {isEvidenceOpen && activeEvidenceTab === "sources"
                    ? "添付文書の根拠を閉じる"
                    : "添付文書の根拠を表示"}
                </span>
                <span {...stylex.props(styles.evidenceCountBadge)}>
                  {message.sources?.length ?? 0}件
                </span>
              </button>
            )}

            {hasJev && message.jevResponse && (
              <button
                type="button"
                onClick={() => onToggleEvidence("jev")}
                aria-pressed={isEvidenceOpen && activeEvidenceTab === "jev"}
                data-jev-toggle="true"
                {...stylex.props(
                  styles.jevToggleButton,
                  isEvidenceOpen &&
                    activeEvidenceTab === "jev" &&
                    styles.jevToggleButtonActive,
                )}
              >
                <span>
                  ⚡{" "}
                  {isEvidenceOpen && activeEvidenceTab === "jev"
                    ? "Jevレスポンスを閉じる"
                    : "Jevレスポンス確認"}
                </span>
                {message.jevResponse.answers?.intent?.choice && (
                  <span {...stylex.props(styles.jevBadge)}>
                    {JEV_INTENT_META[message.jevResponse.answers.intent.choice]?.label ||
                      message.jevResponse.answers.intent.choice}
                    {message.jevResponse.answers.intent.confidence !== undefined
                      ? ` (${Math.round(
                          message.jevResponse.answers.intent.confidence * 100,
                        )}%)`
                      : ""}
                  </span>
                )}
              </button>
            )}
          </div>
        )}

        {message.role === "assistant" && isStreaming && isLast && (
          <span {...stylex.props(styles.cursor)} data-stream-cursor="true" />
        )}
      </div>
    </div>
  );
}
