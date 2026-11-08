"use client";

import * as stylex from "@stylexjs/stylex";
import type { ReactNode } from "react";
import { Button as AriaButton } from "react-aria-components";
import { styles } from "./Button.styles";

export interface ButtonProps {
  children: ReactNode;
  type?: "button" | "submit" | "reset";
  disabled?: boolean;
  variant?: "primary" | "compact" | "text";
  tone?: "neutral" | "positive";
  onActivate?: () => void;
  accessibleLabel?: string;
}

export function Button({
  children,
  type = "button",
  disabled = false,
  variant = "primary",
  tone = "neutral",
  onActivate,
  accessibleLabel,
}: ButtonProps) {
  return (
    <AriaButton
      type={type}
      isDisabled={disabled}
      aria-label={accessibleLabel}
      onPress={onActivate ? () => onActivate() : undefined}
      className={({ isHovered, isDisabled }) =>
        stylex.props(
          styles.base,
          styles[variant],
          tone === "positive" && styles.positive,
          variant === "primary" && isHovered && !isDisabled && styles.hovered,
          isDisabled && styles.disabled,
        ).className ?? ""
      }
    >
      {children}
    </AriaButton>
  );
}
