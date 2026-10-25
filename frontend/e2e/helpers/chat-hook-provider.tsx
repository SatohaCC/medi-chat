import { useState } from "react";
import { createRoot } from "react-dom/client";
import { useChatWebSocket } from "../../features/chat/hooks/useChatWebSocket";

function Harness({ unmount }: { unmount: () => void }) {
  const [selectedModel, setSelectedModel] = useState("gemini:gemini-3.8-flash");
  const [content, setContent] = useState("");
  const chat = useChatWebSocket({ selectedModel });
  return (
    <main>
      <label>
        テストモデル
        <select
          value={selectedModel}
          onChange={(event) => setSelectedModel(event.target.value)}
        >
          <option value="gemini:gemini-3.8-flash">Gemini</option>
          <option value="openai:gpt-5.6-luna">OpenAI</option>
        </select>
      </label>
      <output aria-label="テスト接続">{chat.status}</output>
      <label>
        テスト質問
        <textarea value={content} onChange={(event) => setContent(event.target.value)} />
      </label>
      <button
        type="button"
        disabled={chat.isStreaming}
        onClick={() => chat.sendMessage({ content, productYjCodes: ["3339003F5020"] })}
      >
        テスト送信
      </button>
      <button type="button" onClick={unmount}>
        テスト終了
      </button>
    </main>
  );
}
const container = document.getElementById("harness");
if (!container) throw new Error("Missing test harness container");
const root = createRoot(container);
root.render(<Harness unmount={() => root.unmount()} />);
