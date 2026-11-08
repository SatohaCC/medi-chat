import type { ReactNode } from "react";
import { StatusLight } from "../../ui/StatusLight";
export function StatusIndicator({
  tone,
  children,
}: {
  tone: "positive" | "notice" | "negative";
  children: ReactNode;
}) {
  return <StatusLight variant={tone}>{children}</StatusLight>;
}
