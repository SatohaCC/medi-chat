"use client";
import * as stylex from "@stylexjs/stylex";
import type { ReactNode } from "react";
import { ToggleButton as AriaToggleButton } from "react-aria-components";
import { styles } from "./ToggleButton.styles";
export interface ToggleButtonProps {
  children: ReactNode;
  selected: boolean;
  onSelectedChange: (selected: boolean) => void;
  disabled?: boolean;
  variant?: "medicine" | "custom" | "unregistered";
  accessibleLabel?: string;
}
export function ToggleButton({
  children,
  selected,
  onSelectedChange,
  disabled = false,
  variant = "medicine",
  accessibleLabel,
}: ToggleButtonProps) {
  return (
    <AriaToggleButton
      isSelected={selected}
      onChange={onSelectedChange}
      isDisabled={disabled}
      aria-label={accessibleLabel}
      className={
        stylex.props(
          styles.base,
          variant === "unregistered" && !selected && styles.unregistered,
          selected &&
            (variant === "unregistered"
              ? styles.unregisteredSelected
              : variant === "custom"
                ? styles.customSelected
                : styles.selected),
          disabled && styles.disabled,
        ).className
      }
    >
      {children}
    </AriaToggleButton>
  );
}
