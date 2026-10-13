import * as stylex from "@stylexjs/stylex";
import { AppHeader } from "../../../shared/ui/AppHeader";
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
    <AppHeader>
      <div {...stylex.props(styles.controls)}>
        <Select
          value={selectedModel}
          options={AVAILABLE_MODELS}
          onValueChange={onModelChange}
          label="回答モデル"
        />
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
      </div>
    </AppHeader>
  );
}
