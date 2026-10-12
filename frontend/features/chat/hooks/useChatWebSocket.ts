import { useCallback, useEffect, useRef, useState } from "react";
import { wsBaseUrl } from "../../../shared/api/endpoints";
import { type ChatWebSocketConnection, connectChatWebSocket } from "../api/chatWebSocket";
import type { ConnectionStatus, Message, WsServerMessage } from "../model/chat";

interface UseChatWebSocketOptions {
  selectedModel: string;
  selectedYjCodes: string[];
}

/**
 * Pure helper to immutably patch the latest assistant message in the conversation.
 */
function patchLastAssistant(
  messages: Message[],
  updater: (last: Message) => Message,
): Message[] {
  const lastIndex = messages.length - 1;
  const last = messages[lastIndex];
  if (last?.role !== "assistant") return messages;

  const next = [...messages];
  next[lastIndex] = updater(last);
  return next;
}

function markLatestExchangeInterrupted(messages: Message[]): Message[] {
  const assistantIndex = messages.length - 1;
  const userIndex = assistantIndex - 1;
  const assistant = messages[assistantIndex];
  const user = messages[userIndex];
  if (assistant?.role !== "assistant" || user?.role !== "user") return messages;

  const next = [...messages];
  next[userIndex] = { ...user, isInterrupted: true };
  next[assistantIndex] = { ...assistant, isInterrupted: true };
  return next;
}

export function useChatWebSocket({
  selectedModel,
  selectedYjCodes,
}: UseChatWebSocketOptions) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");

  const connectionRef = useRef<ChatWebSocketConnection | null>(null);
  const activeRequestRef = useRef(false);

  const handleStatusChange = useCallback((nextStatus: ConnectionStatus) => {
    setStatus(nextStatus);
    if (nextStatus !== "disconnected") return;

    if (activeRequestRef.current) {
      activeRequestRef.current = false;
      setMessages(markLatestExchangeInterrupted);
    }
    setIsStreaming(false);
  }, []);

  // Event handler for incoming WebSocket messages - separated from the connection Effect
  const handleServerMessage = useCallback((data: WsServerMessage) => {
    switch (data.type) {
      case "text_delta":
        setMessages((prev) =>
          patchLastAssistant(prev, (last) => ({
            ...last,
            content: last.content + data.content,
          })),
        );
        break;

      case "sources":
        setMessages((prev) =>
          patchLastAssistant(prev, (last) => ({
            ...last,
            sources: data.sources,
          })),
        );
        break;

      case "retrieval_status":
        setMessages((prev) =>
          patchLastAssistant(prev, (last) => ({
            ...last,
            retrievalStatus: data.stage,
            jevResponse: data.jev_response ?? last.jevResponse,
          })),
        );
        break;

      case "jev_response":
        setMessages((prev) =>
          patchLastAssistant(prev, (last) => ({
            ...last,
            jevResponse: data.data,
          })),
        );
        break;

      case "text_done":
        activeRequestRef.current = false;
        setIsStreaming(false);
        break;

      case "error":
        activeRequestRef.current = false;
        setMessages((prev) =>
          patchLastAssistant(prev, (last) => ({
            ...last,
            content: data.content,
            isError: true,
          })),
        );
        setIsStreaming(false);
        break;
    }
  }, []);

  useEffect(() => {
    const connection = connectChatWebSocket(wsBaseUrl(), {
      onStatusChange: handleStatusChange,
      onMessage: handleServerMessage,
    });
    connectionRef.current = connection;

    return () => {
      connectionRef.current = null;
      connection.disconnect();
    };
  }, [handleServerMessage, handleStatusChange]);

  // User action event handler (triggered on form submit, NOT an effect)
  const sendMessage = useCallback(
    (e?: React.FormEvent) => {
      if (e) {
        e.preventDefault();
      }

      const content = input.trim();
      if (!content || selectedYjCodes.length === 0 || isStreaming) {
        return;
      }

      const allMessages: Message[] = [
        ...messages.filter((m) => !m.isError && !m.isInterrupted),
        { role: "user", content },
      ];

      const [provider, model] = selectedModel.split(":");

      const sent = connectionRef.current?.send(
        JSON.stringify({
          type: "message",
          provider,
          model,
          product_yj_codes: selectedYjCodes,
          messages: allMessages.map(({ role, content: msgContent }) => ({
            role,
            content: msgContent,
          })),
        }),
      );
      if (!sent) return;

      activeRequestRef.current = true;
      setMessages([...allMessages, { role: "assistant", content: "" }]);
      setInput("");
      setIsStreaming(true);
    },
    [input, isStreaming, messages, selectedModel, selectedYjCodes],
  );

  return {
    messages,
    setMessages,
    input,
    setInput,
    isStreaming,
    status,
    sendMessage,
  };
}
