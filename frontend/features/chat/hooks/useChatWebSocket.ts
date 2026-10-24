import { useCallback, useEffect, useReducer, useRef } from "react";
import { ensureAuthenticated } from "../../../shared/api/authentication";
import { MAX_MESSAGE_LENGTH } from "../../../shared/api/chatLimits";
import { wsBaseUrl } from "../../../shared/api/endpoints";
import { MAX_TARGET_MEDICINES } from "../../medicine-selection/model/promptSnapshot";
import { type ChatWebSocketConnection, connectChatWebSocket } from "../api/chatWebSocket";
import {
  type ConnectionStatus,
  type WsClientMessage,
  type WsServerMessage,
  parseModelOption,
} from "../model/chat";
import {
  chatReducer,
  initialChatState,
  markLatestExchangeInterrupted,
  patchLastAssistant,
} from "../model/chatReducer";
import { buildRequestHistory } from "../model/requestHistory";

export { assertNever } from "../model/chat";
export { patchLastAssistant, markLatestExchangeInterrupted };

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

export function useChatWebSocket({ selectedModel }: UseChatWebSocketOptions) {
  const [state, dispatch] = useReducer(chatReducer, initialChatState);
  const connectionRef = useRef<ChatWebSocketConnection | null>(null);

  const handleStatusChange = useCallback((status: ConnectionStatus) => {
    dispatch({ type: "status_change", status });
  }, []);

  const handleServerMessage = useCallback((message: WsServerMessage) => {
    dispatch({ type: "server_message", message });
  }, []);

  const handleAuthenticationExpired = useCallback(() => {
    dispatch({ type: "auth_expired" });
  }, []);

  useEffect(() => {
    const connection = connectChatWebSocket(wsBaseUrl(), {
      authorize: ensureAuthenticated,
      onAuthenticationExpired: handleAuthenticationExpired,
      onStatusChange: handleStatusChange,
      onMessage: handleServerMessage,
    });
    connectionRef.current = connection;

    return () => {
      connectionRef.current = null;
      connection.disconnect();
    };
  }, [handleAuthenticationExpired, handleServerMessage, handleStatusChange]);

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
      if (state.status !== "connected" || !connectionRef.current) {
        return { ok: false, reason: "not_connected" };
      }
      if (state.isStreaming || state.activeRequest) {
        return { ok: false, reason: "busy" };
      }

      const requestMessages = buildRequestHistory(state.messages, content);
      const { provider, model } = parseModelOption(selectedModel);

      const clientMessage: WsClientMessage = {
        type: "message",
        provider,
        model,
        product_yj_codes: [...request.productYjCodes],
        messages: requestMessages,
      };

      const sent = connectionRef.current.send(clientMessage);
      if (!sent) {
        return { ok: false, reason: "not_connected" };
      }

      dispatch({ type: "start_message", userContent: content });
      return { ok: true };
    },
    [selectedModel, state.activeRequest, state.isStreaming, state.messages, state.status],
  );

  return {
    messages: state.messages,
    isStreaming: state.isStreaming,
    status: state.status,
    sendMessage,
  };
}
