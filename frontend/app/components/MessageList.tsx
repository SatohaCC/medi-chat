import type { Message } from "../types/chat";
import { MessageItem } from "./MessageItem";

interface MessageListProps {
  messages: Message[];
  isStreaming: boolean;
}

export function MessageList({ messages, isStreaming }: MessageListProps) {
  return (
    <main>
      {messages.length === 0 && (
        <div className="empty">医薬品を選択して、添付文書について質問してください</div>
      )}
      {messages.map((msg, i) => (
        <MessageItem
          key={`msg-${i}`}
          message={msg}
          isStreaming={isStreaming}
          isLast={i === messages.length - 1}
        />
      ))}
    </main>
  );
}
