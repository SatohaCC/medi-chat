"use client";
import * as stylex from "@stylexjs/stylex";
import type { ReactNode } from "react";
import {
  Disclosure as AriaDisclosure,
  Button,
  DisclosurePanel,
} from "react-aria-components";
import { styles } from "./Disclosure.styles";
export interface DisclosureProps {
  title: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
  variant?: "jev" | "source" | "markdown";
}
export function Disclosure({
  title,
  children,
  defaultOpen = false,
  variant = "source",
}: DisclosureProps) {
  return (
    <AriaDisclosure
      defaultExpanded={defaultOpen}
      data-disclosure={variant}
      className={({ isExpanded }) =>
        stylex.props(styles[variant], variant === "jev" && isExpanded && styles.jevOpen)
          .className ?? ""
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
                variant === "jev" ? styles.jevTrigger : styles.sourceTrigger,
                variant === "jev" && isHovered && styles.jevHover,
              ).className ?? ""
            }
          >
            {variant === "markdown" && (
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
