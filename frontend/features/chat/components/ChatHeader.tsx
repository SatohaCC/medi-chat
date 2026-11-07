import { Picker, PickerItem } from "@react-spectrum/s2/Picker";
import { StatusLight } from "@react-spectrum/s2/StatusLight";
import * as stylex from "@stylexjs/stylex";
import { AppHeader } from "../../../shared/ui/AppHeader";
import { AVAILABLE_MODELS, type ConnectionStatus } from "../model/chat";
import { styles } from "./ChatHeader.styles";

interface ChatHeaderProps {
  selectedModel: string;
  onModelChange: (model: string) => void;
  status: ConnectionStatus;
}

export function ChatHeader({ selectedModel, onModelChange, status }: ChatHeaderProps) {
  const statusLabel =
    status === "connected" ? "接続済み" : status === "connecting" ? "接続中" : "未接続";
  const connectionStatus = (
    <StatusLight
      variant={
        status === "connected"
          ? "positive"
          : status === "connecting"
            ? "notice"
            : "negative"
      }
    >
      {statusLabel}
    </StatusLight>
  );
  return (
    <AppHeader
      connectionStatus={connectionStatus}
      connectionNotice={status !== "connected" ? connectionStatus : undefined}
    >
      <div {...stylex.props(styles.controls)}>
        <span>回答モデル</span>
        <Picker
          aria-label="回答モデル"
          value={selectedModel}
          onChange={(key) => {
            if (typeof key === "string") onModelChange(key);
          }}
        >
          {AVAILABLE_MODELS.map((model) => (
            <PickerItem key={model.value} id={model.value}>
              {model.label}
            </PickerItem>
          ))}
        </Picker>
      </div>
    </AppHeader>
  );
}
