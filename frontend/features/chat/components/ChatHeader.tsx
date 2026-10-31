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
      {status}
    </StatusLight>
  );
  return (
    <AppHeader
      connectionStatus={connectionStatus}
      connectionNotice={status !== "connected" ? connectionStatus : undefined}
    >
      <div {...stylex.props(styles.controls)}>
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
