import { useEffect, useOptimistic, useRef, useState, useTransition } from "react";
import { RatingControl } from "../../../../shared/component/RatingControl";
import { type Rating, submitChatFeedback } from "../../api/chatFeedback";
export function AnswerFeedback({ token }: { token: string }) {
  const [rating, setRating] = useState<Rating>(null);
  const [optimisticRating, setOptimisticRating] = useOptimistic(rating);
  const [pending, startTransition] = useTransition();
  const [failed, setFailed] = useState<{ rating: Rating } | null>(null);
  const active = useRef<AbortController | null>(null);

  useEffect(() => () => active.current?.abort(), []);

  function submit(next: Rating) {
    if (active.current || (rating === next && !failed)) return;
    const controller = new AbortController();
    active.current = controller;
    setFailed(null);
    startTransition(async () => {
      setOptimisticRating(next);
      try {
        await submitChatFeedback(token, next, controller.signal);
        if (!controller.signal.aborted) {
          startTransition(() => setRating(next));
        }
      } catch {
        if (!controller.signal.aborted) setFailed({ rating: next });
      } finally {
        if (!controller.signal.aborted) active.current = null;
      }
    });
  }

  return (
    <RatingControl
      value={optimisticRating}
      confirmed={Boolean(rating)}
      disabled={pending}
      onChange={submit}
      error={failed ? "評価を送信できませんでした。" : undefined}
      onRetry={() => {
        if (failed) submit(failed.rating);
      }}
      label="回答への評価"
      pendingLabel="評価を送信中…"
      successLabel="評価を送信しました"
      retryLabel="評価を再試行"
    />
  );
}
