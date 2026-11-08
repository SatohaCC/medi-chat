"use client";
import type { ReactNode } from "react";
import { Button, SpectrumButton } from "../../ui/Button";
export interface ActionButtonProps {
  children: ReactNode;
  onActivate?: () => void;
  disabled?: boolean;
  pending?: boolean;
  type?: "button" | "submit" | "reset";
  accessibleLabel?: string;
  appearance?: "primary" | "secondary" | "solid" | "compact" | "text";
  tone?: "neutral" | "positive";
}
/** Normalizes activation and pending state without exposing a library event. */
export function ActionButton({
  children,
  onActivate,
  disabled,
  pending,
  type,
  accessibleLabel,
  appearance,
  tone,
}: ActionButtonProps) {
  if (appearance === "compact" || appearance === "text" || appearance === "solid")
    return (
      <Button
        type={type}
        disabled={disabled || pending}
        variant={
          appearance === "compact" || appearance === "text" ? appearance : "primary"
        }
        tone={tone}
        onActivate={onActivate}
        accessibleLabel={accessibleLabel}
      >
        {children}
      </Button>
    );
  return (
    <SpectrumButton
      type={type}
      variant={appearance}
      isDisabled={disabled}
      isPending={pending}
      aria-label={accessibleLabel}
      onPress={onActivate ? () => onActivate() : undefined}
    >
      {children}
    </SpectrumButton>
  );
}
