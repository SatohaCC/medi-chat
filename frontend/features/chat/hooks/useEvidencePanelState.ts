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

/**
 * Hook to manage the evidence side panel state, selected tab, and keyword highlighting.
 */
export function useEvidencePanelState({
  messages,
  entries,
  baseline,
  persistentAdditional,
}: UseEvidencePanelStateOptions) {
  const [openEvidenceIndex, setOpenEvidenceIndex] = useState<number | null>(null);
  const [evidencePaneTab, setEvidencePaneTab] = useState<"sources" | "jev">("sources");

  const handleToggleEvidence = useCallback(
    (index: number, tab: "sources" | "jev" = "sources") => {
      if (openEvidenceIndex === index && evidencePaneTab === tab) {
        setOpenEvidenceIndex(null);
      } else {
        setOpenEvidenceIndex(index);
        setEvidencePaneTab(tab);
      }
    },
    [openEvidenceIndex, evidencePaneTab],
  );

  const closeEvidence = useCallback(() => {
    setOpenEvidenceIndex(null);
  }, []);

  const activeEvidenceMessage =
    openEvidenceIndex !== null ? messages[openEvidenceIndex] : undefined;

  const showEvidencePane =
    activeEvidenceMessage?.role === "assistant" &&
    ((Array.isArray(activeEvidenceMessage.sources) &&
      activeEvidenceMessage.sources.length > 0) ||
      Boolean(activeEvidenceMessage.jevResponse) ||
      activeEvidenceMessage.retrievalStatus === "complete");

  const activeUserQuery = useMemo(() => {
    if (openEvidenceIndex === null) return "";
    for (let i = openEvidenceIndex - 1; i >= 0; i--) {
      if (messages[i]?.role === "user") {
        return messages[i].content;
      }
    }
    return "";
  }, [messages, openEvidenceIndex]);

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
    openEvidenceIndex,
    evidencePaneTab,
    setEvidencePaneTab,
    handleToggleEvidence,
    closeEvidence,
    activeEvidenceMessage,
    showEvidencePane,
    evidenceHighlightWords,
  };
}
