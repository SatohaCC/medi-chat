import * as stylex from "@stylexjs/stylex";
import type { ComponentProps, ReactNode } from "react";
import { PageLayout, PageWorkspace } from "../../../../shared/component/PageLayout";
import { ChatInputForm } from "../ChatInputForm";
import { MessageList } from "../MessageList";
import { SourceEvidencePanel } from "../SourceEvidencePanel";
import { ChatDeliveryStatus, type ChatDeliveryStatusProps } from "./ChatDeliveryStatus";
import { styles as layout } from "./ChatScreen.styles";
export interface ChatScreenViewProps {
  header: ReactNode;
  conversation: ComponentProps<typeof MessageList>;
  input: ComponentProps<typeof ChatInputForm>;
  inputKey: number;
  missingSelectedYjCodes: string[];
  delivery: ChatDeliveryStatusProps;
  evidence: ComponentProps<typeof SourceEvidencePanel> | null;
  evidenceKey: string;
}
/** Receives display data and actions; it does not fetch or subscribe. */
export function ChatScreenView({
  header,
  conversation,
  input,
  inputKey,
  missingSelectedYjCodes,
  delivery,
  evidence,
  evidenceKey,
}: ChatScreenViewProps) {
  return (
    <PageLayout screen="chat">
      {header}
      <PageWorkspace>
        <div {...stylex.props(layout.chatColumn)}>
          <MessageList {...conversation} />
          {missingSelectedYjCodes.length > 0 && (
            <p
              role="alert"
              aria-label="選択YJの消失"
              {...stylex.props(layout.missingAlert)}
            >
              選択したYJコードが現在の候補にありません:{" "}
              {missingSelectedYjCodes.join(", ")}。別の薬へ自動変更していません。
            </p>
          )}
          <ChatDeliveryStatus {...delivery} />
          <ChatInputForm key={inputKey} {...input} />
        </div>
        {evidence && <SourceEvidencePanel key={evidenceKey} {...evidence} />}
      </PageWorkspace>
    </PageLayout>
  );
}
