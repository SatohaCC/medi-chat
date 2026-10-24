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

      let message: WsServerMessage;
      try {
        message = JSON.parse(event.data) as WsServerMessage;
      } catch (error) {
        console.error("Failed to parse WebSocket message", error);
        return;
      }
      onMessage(message);
    };

    ws.onclose = (event) => {
      if (!isCurrent()) return;
      socket = null;
      onStatusChange("disconnected");
      if (event?.code === 4001) onAuthenticationExpired?.();
      if (event?.code === 1008) {
        onAuthenticationExpired?.();
        return;
      }

      const delay = Math.min(1000 * 2 ** attempt, 5000) + Math.random() * 1000;
      attempt += 1;
      reconnectTimer = setTimeout(connect, delay);
    };

    ws.onerror = () => {
      if (isCurrent()) ws.close();
    };
  }

  connect();

  return {
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
}
