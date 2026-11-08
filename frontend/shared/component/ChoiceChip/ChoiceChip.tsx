"use client";
import type { ReactNode } from "react";
import { ToggleButton } from "../../ui/ToggleButton";
export interface ChoiceChipProps {
  children: ReactNode;
  selected: boolean;
  onSelectedChange: (selected: boolean) => void;
  disabled?: boolean;
  appearance?: "pill" | "chip" | "mutedChip" | "subtleChip";
  tone?: "accent" | "positive" | "warning";
  accessibleLabel?: string;
}
export function ChoiceChip({ appearance, ...props }: ChoiceChipProps) {
  return <ToggleButton {...props} variant={appearance} />;
}
