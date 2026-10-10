import { AVAILABLE_MODELS, type ConnectionStatus } from "../types/chat";

interface ChatHeaderProps {
  selectedModel: string;
  onModelChange: (model: string) => void;
  status: ConnectionStatus;
}

export function ChatHeader({ selectedModel, onModelChange, status }: ChatHeaderProps) {
  return (
    <header>
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <h1>薬剤師向け 添付文書検索</h1>
        <select
          value={selectedModel}
          onChange={(e) => onModelChange(e.target.value)}
          style={{
            padding: "4px 8px",
            borderRadius: "6px",
            border: "1px solid var(--border)",
            background: "var(--assistant-bg)",
            color: "var(--fg)",
            fontSize: "13px",
            cursor: "pointer",
          }}
        >
          {AVAILABLE_MODELS.map((model) => (
            <option key={model.value} value={model.value}>
              {model.label}
            </option>
          ))}
        </select>
      </div>
      <span className={`status ${status}`}>
        <span className="dot" />
        {status}
      </span>
    </header>
  );
}
