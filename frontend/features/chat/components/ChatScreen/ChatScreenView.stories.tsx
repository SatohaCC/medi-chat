import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { PromptDocument } from "../../../../shared/component/TokenPromptInput/PromptDocument";
import { S2ClientProvider } from "../../../../shared/providers/S2ClientProvider";
import { ChatScreenView } from "./ChatScreenView";

const meta = {
  title: "Chat/Presentation",
  parameters: { layout: "fullscreen" },
} satisfies Meta;
export default meta;
type Story = StoryObj<typeof meta>;
export const Initial: Story = {
  render: () => (
    <S2ClientProvider>
      <ChatScreenView
        header={<header>テスト会話</header>}
        conversation={{ messages: [], isStreaming: false }}
        inputKey={0}
        input={{
          baseline: [],
          onRemoveBaseline() {},
          onClearBaseline() {},
          additional: [],
          onRemoveAdditional() {},
          onClearAdditional() {},
          prompt: new PromptDocument([]),
          onChangePrompt() {},
          onSubmit() {},
          medicineEntries: [],
          status: "connected",
          isStreaming: false,
          canSend: false,
        }}
        missingSelectedYjCodes={[]}
        delivery={{
          pending: null,
          unsent: [],
          restoreChoice: null,
          onCancelPending() {},
          onEdit() {},
          onKeepDraft() {},
          onReplaceDraft() {},
        }}
        evidence={null}
        evidenceKey="test-evidence"
      />
    </S2ClientProvider>
  ),
};
