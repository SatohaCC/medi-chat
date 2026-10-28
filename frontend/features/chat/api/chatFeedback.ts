import { authenticatedFetch } from "../../../shared/api/authentication";
import { backendBaseUrl } from "../../../shared/api/endpoints";

export type Rating = "up" | "down" | null;

export async function submitChatFeedback(
  token: string,
  rating: Rating,
  signal: AbortSignal,
): Promise<void> {
  const response = await authenticatedFetch(`${backendBaseUrl()}/api/chat/feedback`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ feedback_token: token, rating }),
    signal: AbortSignal.any([signal, AbortSignal.timeout(25000)]),
  });
  if (!response.ok) throw new Error("Feedback could not be saved");
  const result: unknown = await response.json();
  if (
    !result ||
    typeof result !== "object" ||
    !("rating" in result) ||
    result.rating !== rating
  ) {
    throw new Error("Feedback acknowledgement is invalid");
  }
}
