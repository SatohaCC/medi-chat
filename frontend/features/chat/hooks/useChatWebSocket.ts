import { useCallback, useEffect, useRef, useState } from "react";
import { ensureAuthenticated } from "../../../shared/api/authentication";
import { MAX_MESSAGE_LENGTH } from "../../../shared/api/chatLimits";
import { wsBaseUrl } from "../../../shared/api/endpoints";
import { MAX_TARGET_MEDICINES } from "../../medicine-selection/model/promptSnapshot";
import { type ChatWebSocketConnection, connectChatWebSocket } from "../api/chatWebSocket";
import type { ConnectionStatus, Message, WsServerMessage } from "../model/chat";
import { buildRequestHistory } from "../model/requestHistory";

export interface SendRequest {
  content: string;
  productYjCodes: readonly string[];
}

export type SendResult =
  | { ok: true }
  | {
      ok: false;
      reason:
        | "not_connected"
        | "empty_target"
        | "busy"
        | "too_many_targets"
        | "message_too_long";
    };

interface UseChatWebSocketOptions {
  selectedModel: string;
  selectedYjCodes?: string[];
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

export function useChatWebSocket({ selectedModel }: UseChatWebSocketOptions) {
  const [messages, setMessages] = useState<Message[]>([]);
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

      case "notices":
        setMessages((prev) =>
          patchLastAssistant(prev, (last) => ({
            ...last,
            notices: data.notices,
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
      authorize: ensureAuthenticated,
      onAuthenticationExpired: () => {
        activeRequestRef.current = false;
        setIsStreaming(false);
        setMessages((prev) =>
          patchLastAssistant(prev, (last) => ({
            ...last,
            content: `${last.content}\n\nログインの有効期限が切れたため、回答を中断しました。必要に応じてもう一度送信してください。`,
            isError: true,
          })),
        );
      },
      onStatusChange: handleStatusChange,
      onMessage: handleServerMessage,
    });
    connectionRef.current = connection;

    return () => {
      connectionRef.current = null;
      connection.disconnect();
    };
  }, [handleServerMessage, handleStatusChange]);

  const sendMessage = useCallback(
    (request: SendRequest): SendResult => {
      const content = request.content.trim();
      if (!content || request.productYjCodes.length === 0) {
        return { ok: false, reason: "empty_target" };
      }
      if (request.productYjCodes.length > MAX_TARGET_MEDICINES) {
        return { ok: false, reason: "too_many_targets" };
      }
      if (Array.from(content).length > MAX_MESSAGE_LENGTH) {
        return { ok: false, reason: "message_too_long" };
      }
      if (status !== "connected" || !connectionRef.current) {
        return { ok: false, reason: "not_connected" };
      }
      if (isStreaming || activeRequestRef.current) {
        return { ok: false, reason: "busy" };
      }

      const requestMessages = buildRequestHistory(messages, content);

      const [provider, model] = selectedModel.split(":");

      const sent = connectionRef.current.send(
        JSON.stringify({
          type: "message",
          provider,
          model,
          product_yj_codes: [...request.productYjCodes],
          messages: requestMessages,
        }),
      );
      if (!sent) {
        return { ok: false, reason: "not_connected" };
      }

      activeRequestRef.current = true;
      setMessages([
        ...messages,
        { role: "user", content },
        { role: "assistant", content: "" },
      ]);
      setIsStreaming(true);
      return { ok: true };
    },
    [isStreaming, messages, selectedModel, status],
  );

  return {
    messages,
    setMessages,
    isStreaming,
    status,
    sendMessage,
  };
}
