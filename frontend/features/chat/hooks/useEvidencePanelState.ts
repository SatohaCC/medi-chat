import { useCallback, useMemo, useState } from "react";
import type { SelectedMedicineItem } from "../../medicine-selection";
import type { Message } from "../model/chat";
import { extractHighlightWords } from "../model/highlightWords";

interface UseEvidencePanelStateOptions {
  messages: readonly Message[];
  entries: readonly { n: string; g: string }[];
  baseline: readonly SelectedMedicineItem[];
  persistentAdditional: readonly SelectedMedicineItem[];
}

function hasMessageEvidence(msg: Message | undefined): boolean {
  return Boolean(
    msg?.role === "assistant" &&
      ((Array.isArray(msg.sources) && msg.sources.length > 0) ||
        Boolean(msg.jevResponse) ||
        msg.retrievalStatus === "complete"),
  );
}

function findLatestEvidenceIndex(messages: readonly Message[]): number {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (hasMessageEvidence(messages[i])) {
      return i;
    }
  }
  return -1;
}

/**
 * Hook to manage the evidence side panel state, selected tab, and keyword highlighting.
 * Automatically opens the side panel when an assistant response with evidence arrives.
 */
export function useEvidencePanelState({
  messages,
  entries,
  baseline,
  persistentAdditional,
}: UseEvidencePanelStateOptions) {
  const [explicitIndex, setExplicitIndex] = useState<number | null>(null);
  const [dismissedLatestEvidenceIndex, setDismissedLatestEvidenceIndex] =
    useState<number | null>(null);
  const [evidencePaneTab, setEvidencePaneTab] = useState<"sources" | "jev">("sources");

  const latestEvidenceIndex = useMemo(
    () => findLatestEvidenceIndex(messages),
    [messages],
  );

  const [prevLatestEvidenceIndex, setPrevLatestEvidenceIndex] =
    useState(latestEvidenceIndex);

  if (latestEvidenceIndex !== prevLatestEvidenceIndex) {
    setPrevLatestEvidenceIndex(latestEvidenceIndex);
    setExplicitIndex(null);
    setDismissedLatestEvidenceIndex(null);
  }

  const effectiveOpenIndex = useMemo(() => {
    if (explicitIndex !== null) {
      return explicitIndex;
    }
    if (
      latestEvidenceIndex !== -1 &&
      dismissedLatestEvidenceIndex !== latestEvidenceIndex
    ) {
      return latestEvidenceIndex;
    }
    return null;
  }, [explicitIndex, latestEvidenceIndex, dismissedLatestEvidenceIndex]);

  const handleToggleEvidence = useCallback(
    (index: number, tab: "sources" | "jev" = "sources") => {
      if (effectiveOpenIndex === index && evidencePaneTab === tab) {
        setExplicitIndex(null);
        setDismissedLatestEvidenceIndex(latestEvidenceIndex);
      } else {
        setExplicitIndex(index);
        setEvidencePaneTab(tab);
      }
    },
    [effectiveOpenIndex, evidencePaneTab, latestEvidenceIndex],
  );

  const closeEvidence = useCallback(() => {
    setExplicitIndex(null);
    setDismissedLatestEvidenceIndex(latestEvidenceIndex);
  }, [latestEvidenceIndex]);

  const activeEvidenceMessage =
    effectiveOpenIndex !== null ? messages[effectiveOpenIndex] : undefined;

  const showEvidencePane = hasMessageEvidence(activeEvidenceMessage);

  const activeUserQuery = useMemo(() => {
    if (effectiveOpenIndex === null) return "";
    for (let i = effectiveOpenIndex - 1; i >= 0; i--) {
      if (messages[i]?.role === "user") {
        return messages[i].content;
      }
    }
    return "";
  }, [messages, effectiveOpenIndex]);

  const activeEvidenceSources = activeEvidenceMessage?.sources;
  const evidenceHighlightWords = useMemo(() => {
    const medicineNames = [
      ...entries.flatMap((entry) => [entry.n, entry.g]),
      ...baseline.map((medicine) => medicine.name),
      ...persistentAdditional.map((medicine) => medicine.name),
      ...(activeEvidenceSources ?? []).flatMap((source) => [
        source.product_name,
        source.generic_name,
      ]),
    ];
    return extractHighlightWords(activeUserQuery, medicineNames);
  }, [activeUserQuery, entries, baseline, persistentAdditional, activeEvidenceSources]);

  return {
    openEvidenceIndex: effectiveOpenIndex,
    evidencePaneTab,
    setEvidencePaneTab,
    handleToggleEvidence,
    closeEvidence,
    activeEvidenceMessage,
    showEvidencePane,
    evidenceHighlightWords,
  };
}
