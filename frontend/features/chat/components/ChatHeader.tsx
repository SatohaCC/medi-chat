import * as stylex from "@stylexjs/stylex";
import { Select } from "../../../shared/ui/Select";
import { AVAILABLE_MODELS, type ConnectionStatus } from "../model/chat";
import { styles } from "./ChatHeader.styles";

interface ChatHeaderProps {
  selectedModel: string;
  onModelChange: (model: string) => void;
  status: ConnectionStatus;
}

export function ChatHeader({ selectedModel, onModelChange, status }: ChatHeaderProps) {
  return (
    <header {...stylex.props(styles.header)}>
      <div {...stylex.props(styles.headingRow)}>
        <h1 {...stylex.props(styles.title)}>薬剤師向け 添付文書検索</h1>
        <Select
          value={selectedModel}
          options={AVAILABLE_MODELS}
          onValueChange={onModelChange}
          label="回答モデル"
        />
      </div>
      <span {...stylex.props(styles.status)}>
        <span
          {...stylex.props(
            styles.dot,
            status === "connected" && styles.connectedDot,
            status === "connecting" && styles.connectingDot,
            status === "disconnected" && styles.disconnectedDot,
          )}
        />
        {status}
      </span>
    </header>
  );
}
