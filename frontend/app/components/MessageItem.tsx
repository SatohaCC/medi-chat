import type { Message } from "../types/chat";
import { AssistantMarkdown } from "./AssistantMarkdown";
import { JevResponseInspector } from "./JevResponseInspector";
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
      className={`message ${message.role} ${message.isError ? "error" : ""} ${
        hasEvidence ? "with-sources" : ""
      }`}
    >
      <div className="bubble">
        {message.role === "assistant" ? (
          <div className="markdown-content">
            <AssistantMarkdown content={message.content} />
          </div>
        ) : (
          <div style={{ whiteSpace: "pre-wrap" }}>{message.content}</div>
        )}

        {message.retrievalStatus && (
          <div
            role="status"
            style={{
              marginTop: "6px",
              fontSize: "12px",
              color: "var(--muted)",
            }}
          >
            {message.retrievalStatus === "jev_searching" && "Jevで根拠を検索中…"}
            {message.retrievalStatus === "complete" && "Jev検索完了"}
            {message.retrievalStatus === "unavailable" && "Jev未接続（ロジック検索のみ）"}
          </div>
        )}

        {message.isInterrupted && message.role === "assistant" && (
          <div
            role="status"
            style={{
              marginTop: "6px",
              fontSize: "12px",
              color: "var(--muted)",
            }}
          >
            通信が切断され、回答が中断されました。未完了の回答です。
          </div>
        )}

        {message.jevResponse && <JevResponseInspector response={message.jevResponse} />}

        {message.role === "assistant" && isStreaming && isLast && (
          <span className="cursor" />
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
