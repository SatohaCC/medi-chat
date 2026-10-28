import * as stylex from "@stylexjs/stylex";
import { ThumbsDown, ThumbsUp } from "lucide-react";
import { useEffect, useOptimistic, useRef, useState, useTransition } from "react";
import {
  Button,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  TooltipTrigger,
} from "react-aria-components";
import { type Rating, submitChatFeedback } from "../api/chatFeedback";
import { styles } from "./AnswerFeedback.styles";

const options = [
  { id: "up", label: "いいね", Icon: ThumbsUp },
  { id: "down", label: "よくない", Icon: ThumbsDown },
] as const;

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
    <div {...stylex.props(styles.row)}>
      <ToggleButtonGroup
        aria-label="回答への評価"
        selectionMode="single"
        selectedKeys={optimisticRating ? [optimisticRating] : []}
        isDisabled={pending}
        onSelectionChange={(keys) => {
          if (keys.has("up")) void submit("up");
          else if (keys.has("down")) void submit("down");
          else void submit(null);
        }}
        {...stylex.props(styles.group)}
      >
        {options.map(({ id, label, Icon }) => (
          <TooltipTrigger key={id} delay={400}>
            <ToggleButton
              id={id}
              aria-label={label}
              className={({ isHovered, isSelected, isFocusVisible, isDisabled }) =>
                stylex.props(
                  styles.button,
                  isHovered && styles.hovered,
                  isSelected && styles.selected,
                  isFocusVisible && styles.focused,
                  isDisabled && styles.disabled,
                ).className ?? ""
              }
            >
              {id === "up" && optimisticRating === "up" ? (
                <span aria-hidden="true" {...stylex.props(styles.likeIcon)}>
                  <span data-like-burst="ring" {...stylex.props(styles.ring)} />
                  <span data-like-burst="particles" {...stylex.props(styles.particles)} />
                  <span data-like-icon="true" {...stylex.props(styles.iconPop)}>
                    <Icon size={17} strokeWidth={1.7} aria-hidden="true" />
                  </span>
                </span>
              ) : (
                <Icon size={17} strokeWidth={1.7} aria-hidden="true" />
              )}
            </ToggleButton>
            <Tooltip placement="top" offset={6} {...stylex.props(styles.tooltip)}>
              {label}
            </Tooltip>
          </TooltipTrigger>
        ))}
      </ToggleButtonGroup>
      <span role="status" {...stylex.props(styles.srOnly)}>
        {pending ? "評価を送信中…" : !failed && rating ? "評価を送信しました" : ""}
      </span>
      {failed && (
        <>
          <span role="alert">評価を送信できませんでした。</span>
          <Button
            {...stylex.props(styles.retry)}
            onPress={() => void submit(failed.rating)}
          >
            評価を再試行
          </Button>
        </>
      )}
    </div>
  );
}
