import { PromptFieldValue } from "@react-spectrum/ai";
import { useState } from "react";
import { createRoot } from "react-dom/client";
import { ChatInputForm } from "../../features/chat/components/ChatInputForm";
import { useChatWebSocket } from "../../features/chat/hooks/useChatWebSocket";
import {
  type SelectedMedicineItem,
  buildPayloadContent,
} from "../../features/medicine-selection";

function ZeroSelection() {
  const [baseline, setBaseline] = useState<SelectedMedicineItem[]>([]);
  const [prompt, setPrompt] = useState<PromptFieldValue>(() => new PromptFieldValue([]));
  const chat = useChatWebSocket({ selectedModel: "openai:gpt-6-luna" });

  const handleSend = (p: PromptFieldValue) => {
    chat.sendMessage({
      content: buildPayloadContent(p),
      productYjCodes: baseline.map((b) => b.yj_code),
    });
  };

  return (
    <>
      <span>{chat.status}</span>
      <button
        type="button"
        onClick={() => setBaseline([{ yj_code: "3339003F5020", name: "イグザレルト錠15mg" }])}
      >
        選択を復帰
      </button>
      <ChatInputForm
        baseline={baseline}
        onRemoveBaseline={(code) => setBaseline((prev) => prev.filter((m) => m.yj_code !== code))}
        onClearBaseline={() => setBaseline([])}
        additional={[]}
        onRemoveAdditional={() => {}}
        onClearAdditional={() => {}}
        prompt={prompt}
        onChangePrompt={setPrompt}
        onSubmit={handleSend}
        medicineEntries={[]}
        status={chat.status}
        isStreaming={chat.isStreaming}
        canSend={baseline.length > 0}
      />
    </>
  );
}

const container = document.getElementById("root");
if (!container) throw new Error("Missing test-only harness root");
createRoot(container).render(<ZeroSelection />);
