export function isUuid4(value: unknown): value is string {
  return (
    typeof value === "string" &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)
  );
}

import type { ConnectionStatus, WsClientMessage, WsServerMessage } from "../model/chat";

export type TransportSendResult = "sent" | "not_open" | "uncertain";
interface VisibilitySource {
  readonly hidden: boolean;
  addEventListener(type: "visibilitychange", callback: () => void): void;
  removeEventListener(type: "visibilitychange", callback: () => void): void;
}
interface ChatWebSocketHandlers {
  onStatusChange: (status: ConnectionStatus) => void;
  onMessage: (message: WsServerMessage) => void;
  authorize?: () => Promise<unknown>;
  onAuthenticationExpired?: () => void;
  onReady?: () => void;
  visibility?: VisibilitySource;
}
export interface ChatWebSocketConnection {
  send: (data: string | WsClientMessage) => TransportSendResult;
  canQueue: () => boolean;
  isReady: () => boolean;
  disconnect: () => void;
  [Symbol.dispose]?: () => void;
}

/**
 * Type guard validating that unknown data conforms to WsServerMessage.
 */
export function isWsServerMessage(data: unknown): data is WsServerMessage {
  if (typeof data !== "object" || data === null) {
    return false;
  }

  const candidate = data as {
    type?: unknown;
    request_id?: unknown;
    ping_id?: unknown;
    code?: unknown;
    content?: unknown;
    feedback_token?: unknown;
  };
  if (typeof candidate.type !== "string") {
    return false;
  }

  if (candidate.type === "pong") return isUuid4(candidate.ping_id);
  if (candidate.type === "connection_error")
    return (
      ["invalid_payload", "unsupported_type"].includes(String(candidate.code)) &&
      typeof candidate.content === "string"
    );
  if (!isUuid4(candidate.request_id)) return false;
  if (candidate.type === "control_error")
    return (
      ["busy", "not_active"].includes(String(candidate.code)) &&
      typeof candidate.content === "string"
    );
  switch (candidate.type) {
    case "text_delta":
      return typeof (candidate as { content?: unknown }).content === "string";
    case "aborted":
      return true;
    case "text_done":
      return (
        candidate.feedback_token == null || typeof candidate.feedback_token === "string"
      );
    case "sources":
      return Array.isArray((candidate as { sources?: unknown }).sources);
    case "retrieval_status":
      return typeof (candidate as { stage?: unknown }).stage === "string";
    case "jev_response":
      return (
        typeof (candidate as { data?: unknown }).data === "object" &&
        (candidate as { data?: unknown }).data !== null
      );
    case "notices":
      return Array.isArray((candidate as { notices?: unknown }).notices);
    case "error":
      return typeof (candidate as { content?: unknown }).content === "string";
    default:
      return false;
  }
}

/** Owns one socket generation, retry, heartbeat and visibility subscription. */
export function connectChatWebSocket(
  url: string,
  handlers: ChatWebSocketHandlers,
): ChatWebSocketConnection {
  const { onStatusChange, onMessage, authorize, onAuthenticationExpired, onReady } =
    handlers;
  const visibility =
    handlers.visibility ?? (typeof document === "undefined" ? undefined : document);
  let stopped = false;
  let blocked = false;
  let ready = false;
  let socket: WebSocket | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
  let idleTimer: ReturnType<typeof setTimeout> | undefined;
  let pongTimer: ReturnType<typeof setTimeout> | undefined;
  let outstanding: string | null = null;
  let probeGeneration = 0;
  let attempt = 0;

  function clearHeartbeat() {
    clearTimeout(idleTimer);
    clearTimeout(pongTimer);
    outstanding = null;
    probeGeneration += 1;
  }
  function invalidate(ws: WebSocket, code?: number) {
    if (stopped || socket !== ws) return;
    socket = null;
    ready = false;
    clearHeartbeat();
    if (code === 4001 || code === 1008) {
      blocked = true;
      onAuthenticationExpired?.();
    }
    onStatusChange("disconnected");
    ws.close();
    if (code === 1008) return;
    const delay = Math.min(1000 * 2 ** attempt, 5000) + Math.random() * 1000;
    attempt += 1;
    reconnectTimer = setTimeout(connect, delay);
  }
  function idle(ws: WebSocket) {
    clearTimeout(idleTimer);
    if (stopped || socket !== ws || visibility?.hidden || outstanding) return;
    const generation = probeGeneration;
    idleTimer = setTimeout(() => {
      if (generation === probeGeneration && socket === ws) ping(ws);
    }, 30000);
  }
  function ping(ws: WebSocket) {
    if (stopped || socket !== ws || visibility?.hidden || outstanding) return;
    const pingId = crypto.randomUUID();
    outstanding = pingId;
    const generation = ++probeGeneration;
    try {
      ws.send(JSON.stringify({ type: "ping", ping_id: pingId }));
    } catch {
      invalidate(ws);
      return;
    }
    pongTimer = setTimeout(() => {
      if (generation === probeGeneration && outstanding === pingId) invalidate(ws);
    }, 5000);
  }
  function visibilityChanged() {
    clearHeartbeat();
    if (!socket || stopped) return;
    if (!visibility?.hidden && socket.readyState === WebSocket.OPEN) {
      ready = false;
      ping(socket);
    }
  }
  function connect() {
    if (stopped) return;
    if (authorize)
      void authorize()
        .then(() => {
          if (!stopped) open();
        })
        .catch(() => {
          if (!stopped) {
            blocked = true;
            onAuthenticationExpired?.();
            onStatusChange("disconnected");
          }
        });
    else open();
  }
  function open() {
    if (stopped) return;
    onStatusChange("connecting");
    const ws = new WebSocket(url);
    socket = ws;
    const current = () => !stopped && socket === ws;
    ws.onopen = () => {
      if (!current()) return;
      attempt = 0;
      blocked = false;
      ready = !visibility?.hidden;
      onStatusChange("connected");
      idle(ws);
      if (ready) onReady?.();
    };
    ws.onmessage = (event) => {
      if (!current()) return;
      let raw: unknown;
      try {
        raw = JSON.parse(event.data);
      } catch (error) {
        console.error("Failed to parse WebSocket message", error);
        return;
      }
      if (!isWsServerMessage(raw)) {
        console.warn("Unrecognized or malformed WebSocket message", raw);
        return;
      }
      if (raw.type === "pong") {
        if (raw.ping_id !== outstanding) return;
        clearHeartbeat();
        ready = true;
        idle(ws);
        onReady?.();
        return;
      }
      if (raw.type !== "connection_error" && raw.type !== "control_error") idle(ws);
      onMessage(raw);
    };
    ws.onclose = (event) => {
      if (current()) invalidate(ws, event?.code);
    };
    ws.onerror = () => {
      if (current()) invalidate(ws);
    };
  }
  visibility?.addEventListener("visibilitychange", visibilityChanged);
  connect();
  const connection: ChatWebSocketConnection = {
    send(data) {
      const ws = socket;
      if (stopped || !ready || ws?.readyState !== WebSocket.OPEN) return "not_open";
      try {
        ws.send(typeof data === "string" ? data : JSON.stringify(data));
        return "sent";
      } catch {
        invalidate(ws);
        return "uncertain";
      }
    },
    canQueue: () => !stopped && !blocked,
    isReady: () => ready && !stopped && socket?.readyState === WebSocket.OPEN,
    disconnect() {
      if (stopped) return;
      stopped = true;
      ready = false;
      clearTimeout(reconnectTimer);
      clearHeartbeat();
      visibility?.removeEventListener("visibilitychange", visibilityChanged);
      const ws = socket;
      socket = null;
      ws?.close();
    },
  };
  if (typeof Symbol !== "undefined" && "dispose" in Symbol)
    connection[Symbol.dispose] = () => connection.disconnect();
  return connection;
}
