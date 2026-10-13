import * as stylex from "@stylexjs/stylex";
import type { Message } from "../model/chat";
import { MessageItem } from "./MessageItem";
import { styles } from "./MessageList.styles";

interface MessageListProps {
  messages: Message[];
  isStreaming: boolean;
  containerRef?: React.RefObject<HTMLElement | null>;
}

export function MessageList({ messages, isStreaming, containerRef }: MessageListProps) {
  return (
    <main
      ref={containerRef}
      {...stylex.props(styles.root, messages.length > 0 && styles.withBottomPadding)}
    >
      {messages.length === 0 && (
        <div {...stylex.props(styles.empty)}>
          医薬品を選択して、添付文書について質問してください
        </div>
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
