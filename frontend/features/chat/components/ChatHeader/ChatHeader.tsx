import * as stylex from "@stylexjs/stylex";
import { SelectField } from "../../../../shared/component/SelectField";
import { StatusIndicator as StatusLight } from "../../../../shared/component/StatusIndicator";
import { AppHeader } from "../../../app-shell/components/AppHeader";
import { AVAILABLE_MODELS, type ConnectionStatus } from "../../model/chat";
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
      tone={
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
        <SelectField
          label="回答モデル"
          value={selectedModel}
          onChange={onModelChange}
          options={AVAILABLE_MODELS}
        />
      </div>
    </AppHeader>
  );
}
