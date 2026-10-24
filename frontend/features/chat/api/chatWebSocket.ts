import type { ConnectionStatus, WsServerMessage } from "../model/chat";

interface ChatWebSocketHandlers {
  onStatusChange: (status: ConnectionStatus) => void;
  onMessage: (message: WsServerMessage) => void;
  authorize?: () => Promise<unknown>;
  onAuthenticationExpired?: () => void;
}

export interface ChatWebSocketConnection {
  send: (data: string) => boolean;
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

  const candidate = data as { type?: unknown };
  if (typeof candidate.type !== "string") {
    return false;
  }

  switch (candidate.type) {
    case "text_delta":
      return typeof (candidate as { content?: unknown }).content === "string";
    case "text_done":
      return true;
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

/** Owns the socket and retry timer for one connection lifecycle. */
export function connectChatWebSocket(
  url: string,
  {
    onStatusChange,
    onMessage,
    authorize,
    onAuthenticationExpired,
  }: ChatWebSocketHandlers,
): ChatWebSocketConnection {
  let stopped = false;
  let socket: WebSocket | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
  let attempt = 0;

  function connect() {
    if (stopped) return;
    if (authorize) {
      void authorize()
        .then(() => {
          if (!stopped) open();
        })
        .catch(() => {
          if (!stopped) onStatusChange("disconnected");
        });
    } else open();
  }

  function open() {
    onStatusChange("connecting");
    const ws = new WebSocket(url);
    socket = ws;
    const isCurrent = () => !stopped && socket === ws;

    ws.onopen = () => {
      if (!isCurrent()) return;
      attempt = 0;
      onStatusChange("connected");
    };

    ws.onmessage = (event) => {
      if (!isCurrent()) return;

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

      onMessage(raw);
    };

    ws.onclose = (event) => {
      if (!isCurrent()) return;
      socket = null;
      // Report the cause before disconnected clears the active exchange state.
      if (event?.code === 4001 || event?.code === 1008) {
        onAuthenticationExpired?.();
      }
      onStatusChange("disconnected");
      if (event?.code === 1008) return;

      const delay = Math.min(1000 * 2 ** attempt, 5000) + Math.random() * 1000;
      attempt += 1;
      reconnectTimer = setTimeout(connect, delay);
    };

    ws.onerror = () => {
      if (isCurrent()) ws.close();
    };
  }

  connect();

  const connection: ChatWebSocketConnection = {
    send(data) {
      if (stopped || socket?.readyState !== WebSocket.OPEN) return false;
      socket.send(data);
      return true;
    },
    disconnect() {
      stopped = true;
      clearTimeout(reconnectTimer);
      const ws = socket;
      socket = null;
      ws?.close();
    },
  };

  if (typeof Symbol !== "undefined" && "dispose" in Symbol) {
    connection[Symbol.dispose] = () => {
      connection.disconnect();
    };
  }

  return connection;
}
