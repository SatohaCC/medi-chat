import * as stylex from "@stylexjs/stylex";
import type { Message } from "../model/chat";
import { AssistantMarkdown } from "./AssistantMarkdown";
import { JevResponseInspector } from "./JevResponseInspector";
import { styles } from "./MessageItem.styles";
import { SourceEvidencePanel } from "./SourceEvidencePanel";

interface MessageItemProps {
  message: Message;
  isStreaming: boolean;
  isLast: boolean;
}

export function MessageItem({ message, isStreaming, isLast }: MessageItemProps) {
  const hasEvidence =
    message.role === "assistant" &&
    ((Array.isArray(message.sources) && message.sources.length > 0) ||
      Boolean(message.jevResponse) ||
      message.retrievalStatus === "complete");

  return (
    <div
      {...stylex.props(
        styles.message,
        message.role === "user" && styles.user,
        hasEvidence && styles.withSources,
      )}
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

        {message.jevResponse && <JevResponseInspector response={message.jevResponse} />}

        {message.role === "assistant" && isStreaming && isLast && (
          <span {...stylex.props(styles.cursor)} data-stream-cursor="true" />
        )}
      </div>

      {hasEvidence && (
        <SourceEvidencePanel
          sources={message.sources || []}
          retrievalStatus={message.retrievalStatus}
          jevResponse={message.jevResponse}
        />
      )}
    </div>
  );
}
