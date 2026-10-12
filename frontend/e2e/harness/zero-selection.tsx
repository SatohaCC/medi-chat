import { useState } from "react";
import { createRoot } from "react-dom/client";
import { ChatInputForm } from "../../features/chat/components/ChatInputForm";
import { useChatWebSocket } from "../../features/chat/hooks/useChatWebSocket";

function ZeroSelection() {
  const [selectedYjCodes, setSelectedYjCodes] = useState<string[]>([]);
  const chat = useChatWebSocket({ selectedModel: "openai:gpt-6-luna", selectedYjCodes });
  return (
    <>
      <span>{chat.status}</span>
      <button type="button" onClick={() => setSelectedYjCodes(["3339003F5020"])}>
        選択を復帰
      </button>
      <ChatInputForm
        input={chat.input}
        onChangeInput={chat.setInput}
        onSubmit={chat.sendMessage}
        onSelectMedicine={() => {}}
        selectedYjCodes={selectedYjCodes}
        status={chat.status}
        isStreaming={chat.isStreaming}
      />
    </>
  );
}

const container = document.getElementById("root");
if (!container) throw new Error("Missing test-only harness root");
createRoot(container).render(<ZeroSelection />);
