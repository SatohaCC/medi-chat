import * as stylex from "@stylexjs/stylex";
import { ThumbsDown, ThumbsUp } from "lucide-react";
import { AriaButton as Button } from "../../ui/Button";
import {
  AriaToggleButton as ToggleButton,
  ToggleButtonGroup,
} from "../../ui/ToggleButton";
import { Tooltip, TooltipTrigger } from "../../ui/Tooltip";
import { styles } from "./RatingControl.styles";

const options = [
  { id: "up", label: "いいね", Icon: ThumbsUp },
  { id: "down", label: "よくない", Icon: ThumbsDown },
] as const;

export type RatingValue = "up" | "down" | null;
export interface RatingControlProps {
  value: RatingValue;
  confirmed: boolean;
  disabled: boolean;
  error?: string;
  onChange: (value: RatingValue) => void;
  onRetry?: () => void;
  label: string;
  pendingLabel: string;
  successLabel: string;
  retryLabel: string;
}
export function RatingControl({
  value,
  confirmed,
  disabled,
  error,
  onChange,
  onRetry,
  label,
  pendingLabel,
  successLabel,
  retryLabel,
}: RatingControlProps) {
  return (
    <div {...stylex.props(styles.row)}>
      <ToggleButtonGroup
        aria-label={label}
        selectionMode="single"
        selectedKeys={value ? [value] : []}
        isDisabled={disabled}
        onSelectionChange={(keys) => {
          if (keys.has("up")) onChange("up");
          else if (keys.has("down")) onChange("down");
          else onChange(null);
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
              {id === "up" && value === "up" ? (
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
        {disabled ? pendingLabel : !error && confirmed ? successLabel : ""}
      </span>
      {error && (
        <>
          <span role="alert">{error}</span>
          <Button {...stylex.props(styles.retry)} onPress={() => onRetry?.()}>
            {retryLabel}
          </Button>
        </>
      )}
    </div>
  );
}
