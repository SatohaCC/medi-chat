import type { ReactNode } from "react";
import { Content, Heading, InlineAlert } from "../../ui/InlineAlert";
export function Notice({
  title,
  children,
  tone = "negative",
}: {
  title: string;
  children: ReactNode;
  tone?: "negative" | "positive" | "notice" | "neutral";
}) {
  return (
    <InlineAlert variant={tone}>
      <Heading>{title}</Heading>
      <Content>{children}</Content>
    </InlineAlert>
  );
}
