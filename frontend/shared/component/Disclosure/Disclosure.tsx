"use client";
import * as stylex from "@stylexjs/stylex";
import type { ReactNode } from "react";
import { AriaButton as Button } from "../../ui/Button";
import { Disclosure as AriaDisclosure, DisclosurePanel } from "../../ui/Disclosure";
import { styles } from "./Disclosure.styles";
export interface DisclosureProps {
  title: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
  variant?: "accent" | "surface" | "spaced";
}
export function Disclosure({
  title,
  children,
  defaultOpen = false,
  variant = "surface",
}: DisclosureProps) {
  return (
    <AriaDisclosure
      defaultExpanded={defaultOpen}
      data-disclosure={variant}
      className={({ isExpanded }) =>
        stylex.props(
          styles[variant],
          variant === "accent" && isExpanded && styles.accentOpen,
        ).className ?? ""
      }
    >
      {({ isExpanded }) => (
        <>
          <Button
            slot="trigger"
            data-disclosure-trigger="true"
            className={({ isHovered }) =>
              stylex.props(
                styles.trigger,
                variant === "accent" ? styles.accentTrigger : styles.surfaceTrigger,
                variant === "accent" && isHovered && styles.accentHover,
              ).className ?? ""
            }
          >
            {variant === "spaced" && (
              <span aria-hidden="true" {...stylex.props(styles.marker)}>
                {isExpanded ? "▼" : "▶"}
              </span>
            )}
            {title}
          </Button>
          <DisclosurePanel>{children}</DisclosurePanel>
        </>
      )}
    </AriaDisclosure>
  );
}
