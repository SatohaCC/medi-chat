import type { ConnectionStatus, Message, WsServerMessage } from "./chat";

export function assertNever(x: never): never {
  throw new Error(`Unexpected discriminated union member: ${JSON.stringify(x)}`);
}

export interface ChatState {
  readonly messages: Message[];
  readonly isStreaming: boolean;
  readonly status: ConnectionStatus;
  readonly activeRequest: boolean;
}

export const initialChatState: ChatState = {
  messages: [],
  isStreaming: false,
  status: "disconnected",
  activeRequest: false,
};

export type ChatAction =
  | { type: "server_message"; message: WsServerMessage }
  | { type: "start_message"; userContent: string }
  | { type: "status_change"; status: ConnectionStatus }
  | { type: "auth_expired" };

export function patchLastAssistant(
  messages: readonly Message[],
  updater: (last: Message) => Message,
): Message[] {
  const lastIndex = messages.length - 1;
  const last = messages[lastIndex];
  if (last?.role !== "assistant") return [...messages];

  const next = [...messages];
  next[lastIndex] = updater(last);
  return next;
}

export function markLatestExchangeInterrupted(
  messages: readonly Message[],
): Message[] {
  const assistantIndex = messages.length - 1;
  const userIndex = assistantIndex - 1;
  const assistant = messages[assistantIndex];
  const user = messages[userIndex];
  if (assistant?.role !== "assistant" || user?.role !== "user") {
    return [...messages];
  }

  const next = [...messages];
  next[userIndex] = { ...user, isInterrupted: true };
  next[assistantIndex] = { ...assistant, isInterrupted: true };
  return next;
}

export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "server_message": {
      const { message } = action;
      switch (message.type) {
        case "text_delta":
          return {
            ...state,
            messages: patchLastAssistant(state.messages, (last) => ({
              ...last,
              content: last.content + message.content,
            })),
          };

        case "sources":
          return {
            ...state,
            messages: patchLastAssistant(state.messages, (last) => ({
              ...last,
              sources: message.sources,
            })),
          };

        case "retrieval_status":
          return {
            ...state,
            messages: patchLastAssistant(state.messages, (last) => ({
              ...last,
              retrievalStatus: message.stage,
              jevResponse: message.jev_response ?? last.jevResponse,
            })),
          };

        case "jev_response":
          return {
            ...state,
            messages: patchLastAssistant(state.messages, (last) => ({
              ...last,
              jevResponse: message.data,
            })),
          };

        case "notices":
          return {
            ...state,
            messages: patchLastAssistant(state.messages, (last) => ({
              ...last,
              notices: message.notices,
            })),
          };

        case "text_done":
          return {
            ...state,
            activeRequest: false,
            isStreaming: false,
          };

        case "error":
          return {
            ...state,
            activeRequest: false,
            isStreaming: false,
            messages: patchLastAssistant(state.messages, (last) => ({
              ...last,
              content: message.content,
              isError: true,
            })),
          };

        default:
          return assertNever(message);
      }
    }

    case "start_message":
      return {
        ...state,
        activeRequest: true,
        isStreaming: true,
        messages: [
          ...state.messages,
          { role: "user", content: action.userContent },
          { role: "assistant", content: "" },
        ],
      };

    case "status_change": {
      const nextStatus = action.status;
      if (nextStatus !== "disconnected") {
        return {
          ...state,
          status: nextStatus,
        };
      }
      return {
        ...state,
        status: "disconnected",
        activeRequest: false,
        isStreaming: false,
        messages: state.activeRequest
          ? markLatestExchangeInterrupted(state.messages)
          : state.messages,
      };
    }

    case "auth_expired": {
      if (!state.activeRequest) return state;
      return {
        ...state,
        activeRequest: false,
        isStreaming: false,
        messages: patchLastAssistant(
          markLatestExchangeInterrupted(state.messages),
          (last) => ({
            ...last,
            content: `${last.content}\n\nログインの有効期限が切れたため、回答を中断しました。必要に応じてもう一度送信してください。`,
            isError: true,
          }),
        ),
      };
    }

    default:
      return assertNever(action);
  }
}
