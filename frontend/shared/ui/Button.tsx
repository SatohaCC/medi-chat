"use client";

import * as stylex from "@stylexjs/stylex";
import type { ReactNode } from "react";
import { Button as AriaButton } from "react-aria-components";
import { styles } from "./Button.styles";

export interface ButtonProps {
  children: ReactNode;
  type?: "button" | "submit" | "reset";
  disabled?: boolean;
  selected?: boolean;
  variant?: "primary" | "copy" | "copySuccess" | "text" | "filterAll" | "filterSection";
  onActivate?: () => void;
  accessibleLabel?: string;
}

export function Button({
  children,
  type = "button",
  disabled = false,
  selected = false,
  variant = "primary",
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
          styles[variant],
          selected && variant === "filterAll" && styles.filterAllSelected,
          selected && variant === "filterSection" && styles.filterSectionSelected,
          variant === "primary" && isHovered && !isDisabled && styles.hovered,
          isDisabled && styles.disabled,
        ).className ?? ""
      }
    >
      {children}
    </AriaButton>
  );
}
