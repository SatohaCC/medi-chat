import { MAX_MESSAGE_LENGTH } from "../../../shared/api/chatLimits";
import type { Message } from "./chat";

const MAX_HISTORY_TURNS = 24;

/** Preserve complete, unmodified exchanges within the server's 50-message limit. */
export function buildRequestHistory(
  history: readonly Message[],
  content: string,
): Pick<Message, "role" | "content">[] {
  const turns: Pick<Message, "role" | "content">[][] = [];
  for (let index = 0; index < history.length - 1; index++) {
    const user = history[index];
    const assistant = history[index + 1];
    if (user.role !== "user" || assistant.role !== "assistant") continue;
    if (
      [user, assistant].some(
        (message) =>
          message.isError ||
          message.isInterrupted ||
          !message.content.trim() ||
          Array.from(message.content).length > MAX_MESSAGE_LENGTH,
      )
    )
      continue;
    turns.push([user, assistant].map(({ role, content }) => ({ role, content })));
  }
  return [...turns.slice(-MAX_HISTORY_TURNS).flat(), { role: "user", content }];
}
