import { useCallback, useEffect, useReducer, useRef, useState } from "react";
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
import {
  ChatRequestLifecycle,
  type PendingRequest,
  type RequestContext,
  type UnsentRequest,
} from "../model/chatRequestLifecycle";
import { buildRequestHistory } from "../model/requestHistory";

export { assertNever } from "../model/chat";
export { patchLastAssistant, markLatestExchangeInterrupted };

export interface SendRequest {
  content: string;
  productYjCodes: readonly string[];
  context?: RequestContext;
}

export type SendResult =
  | { ok: true; disposition: "sent" | "queued"; requestId: string }
  | {
      ok: false;
      reason:
        | "queue_full"
        | "uncertain"
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
  const lifecycleRef = useRef<ChatRequestLifecycle | null>(null);
  const [pending, setPending] = useState<PendingRequest | null>(null);
  const [unsent, setUnsent] = useState<UnsentRequest[]>([]);

  const handleStatusChange = useCallback((status: ConnectionStatus) => {
    if (status === "disconnected") {
      lifecycleRef.current?.disconnected();
    }
    dispatch({ type: "status_change", status });
  }, []);

  const handleServerMessage = useCallback((message: WsServerMessage) => {
    lifecycleRef.current?.receive(message);
  }, []);

  const handleAuthenticationExpired = useCallback(() => {
    lifecycleRef.current?.authenticationExpired();
    dispatch({ type: "auth_expired" });
  }, []);

  useEffect(() => {
    const lifecycle = new ChatRequestLifecycle({
      send: (payload) => connectionRef.current?.send(payload) ?? "not_open",
      ready: () => connectionRef.current?.isReady() ?? false,
      canQueue: () => connectionRef.current?.canQueue() ?? true,
      start: (userContent, requestId) =>
        dispatch({ type: "start_message", userContent, requestId }),
      abort: (request_id) =>
        connectionRef.current?.send(JSON.stringify({ type: "abort", request_id })) ===
        "sent",
      event: (message) => dispatch({ type: "server_message", message }),
      pending: (next, rejected) => {
        setPending(next);
        if (rejected) setUnsent((previous) => [...previous, rejected]);
      },
    });
    lifecycleRef.current = lifecycle;
    const connection = connectChatWebSocket(wsBaseUrl(), {
      authorize: ensureAuthenticated,
      onAuthenticationExpired: handleAuthenticationExpired,
      onStatusChange: handleStatusChange,
      onMessage: handleServerMessage,
      onReady: () => lifecycle.flush(),
    });
    connectionRef.current = connection;

    return () => {
      lifecycle.dispose();
      lifecycleRef.current = null;
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
      if (
        !connectionRef.current ||
        (state.status === "connected" && !connectionRef.current.isReady())
      ) {
        return { ok: false, reason: "not_connected" };
      }
      // Check both React state and synchronous ref to prevent overlapping sends in the same tick
      if (state.isStreaming || lifecycleRef.current?.activeId) {
        return { ok: false, reason: "busy" };
      }

      const requestMessages = buildRequestHistory(state.messages, content);
      const { provider, model } = parseModelOption(selectedModel);

      const clientMessage: WsClientMessage = {
        type: "message",
        request_id: crypto.randomUUID(),
        provider,
        model,
        product_yj_codes: [...request.productYjCodes],
        messages: requestMessages,
      };

      return (
        lifecycleRef.current?.send(clientMessage, content, request.context) ?? {
          ok: false,
          reason: "not_connected",
        }
      );
    },
    [selectedModel, state.isStreaming, state.messages, state.status],
  );

  const abortRequest = useCallback(() => {
    if (lifecycleRef.current?.abort()) dispatch({ type: "stop_request" });
  }, []);

  const cancelPending = useCallback(
    (requestId: string) => lifecycleRef.current?.cancelPending(requestId),
    [],
  );

  return {
    pending,
    unsent,
    cancelPending,
    abortRequest,
    isStopping: state.isStopping,
    messages: state.messages,
    isStreaming: state.isStreaming,
    status: state.status,
    sendMessage,
  };
}
