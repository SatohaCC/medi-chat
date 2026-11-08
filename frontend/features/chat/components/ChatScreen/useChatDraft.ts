import { useCallback, useMemo, useState } from "react";
import { PromptDocument } from "../../../../shared/component/TokenPromptInput/PromptDocument";
import {
  buildPayloadContent,
  computeTargetMedicines,
  extractMentionsFromSegments,
  resolvePostSendState,
  type SelectedMedicineItem,
  useMedicineEntries,
} from "../../../medicine-selection";
import type { UnsentRequest } from "../../model/chatRequestLifecycle";
/** Owns the draft, medicine selection and atomic restoration of an unsent question. */
export function useChatDraft() {
  const [selectedModel, setSelectedModel] = useState("openai:gpt-6-luna");

  const { entries, activeMedicines } = useMedicineEntries();

  const [baseline, setBaseline] = useState<SelectedMedicineItem[]>([]);
  const [persistentAdditional, setPersistentAdditional] = useState<
    SelectedMedicineItem[]
  >([]);
  const [prompt, setPrompt] = useState<PromptDocument>(() => new PromptDocument([]));
  const [inputKey, setInputKey] = useState(0);
  const [restoreChoice, setRestoreChoice] = useState<UnsentRequest | null>(null);

  const availableActiveYjCodes = useMemo(() => {
    return new Set(activeMedicines.items.map((entry) => entry.y));
  }, [activeMedicines.items]);

  const missingSelectedYjCodes = useMemo(() => {
    if (activeMedicines.status !== "ready") return [];
    return baseline
      .map((b) => b.yj_code)
      .filter((code) => !availableActiveYjCodes.has(code));
  }, [activeMedicines.status, baseline, availableActiveYjCodes]);

  const mentions = useMemo(() => {
    return extractMentionsFromSegments(prompt.segments);
  }, [prompt]);

  const targetState = useMemo(() => {
    return computeTargetMedicines({
      baseline,
      persistentAdditional,
      mentions,
    });
  }, [baseline, persistentAdditional, mentions]);

  const restoreQuestion = (question: UnsentRequest) => {
    if (!question.context) return;
    setPrompt(new PromptDocument([...question.context.promptSegments]));
    setBaseline(question.context.targets.map((medicine) => ({ ...medicine })));
    setSelectedModel(question.context.model);
    setPersistentAdditional([]);
    setInputKey((previous) => previous + 1);
    setRestoreChoice(null);
  };

  const handleAddBaseline = useCallback((medicine: SelectedMedicineItem) => {
    setBaseline((prev) => {
      if (prev.some((m) => m.yj_code === medicine.yj_code)) return prev;
      return [...prev, medicine];
    });
  }, []);

  const handleRemoveBaseline = useCallback((yjCode: string) => {
    setBaseline((prev) => prev.filter((m) => m.yj_code !== yjCode));
    setPersistentAdditional([]);
  }, []);

  const handleClearBaseline = useCallback(() => {
    setBaseline([]);
    setPersistentAdditional([]);
  }, []);

  const handleRemoveAdditional = useCallback(
    (yjCode: string) => {
      if (mentions.some((m) => m.yj_code === yjCode)) {
        const remaining = prompt.segments.filter((seg) => {
          if (seg.type === "token") {
            const val = seg.value;
            if (
              val &&
              typeof val === "object" &&
              "type" in val &&
              val.type === "custom"
            ) {
              const data =
                "data" in val && val.data && typeof val.data === "object"
                  ? (val.data as { yj_code?: string })
                  : undefined;
              return data?.yj_code !== yjCode;
            }
          }
          return true;
        });
        setPrompt(new PromptDocument(remaining));
      } else {
        setPersistentAdditional((prev) => prev.filter((m) => m.yj_code !== yjCode));
      }
    },
    [mentions, prompt],
  );

  const handleClearAdditional = useCallback(() => {
    setPersistentAdditional([]);
    const baselineYjSet = new Set(baseline.map((b) => b.yj_code));
    const remaining = prompt.segments.filter((seg) => {
      if (seg.type === "token") {
        const val = seg.value;
        if (val && typeof val === "object" && "type" in val && val.type === "custom") {
          const data =
            "data" in val && val.data && typeof val.data === "object"
              ? (val.data as { yj_code?: string })
              : undefined;
          return data?.yj_code ? baselineYjSet.has(data.yj_code) : false;
        }
      }
      return true;
    });
    setPrompt(new PromptDocument(remaining));
  }, [baseline, prompt]);

  const handleChangePrompt = useCallback((nextPrompt: PromptDocument) => {
    const newMentions = extractMentionsFromSegments(nextPrompt.segments);
    if (newMentions.length > 0) {
      setPersistentAdditional([]);
    }
    setPrompt(nextPrompt);
  }, []);

  const handleSelectSuggestion = useCallback((promptText: string) => {
    setPrompt(new PromptDocument([{ type: "text", text: promptText }]));
  }, []);

  const commitSent = () => {
    const postState = resolvePostSendState(targetState);
    setPersistentAdditional(postState.persistentAdditional);
    setPrompt(new PromptDocument([]));
    setInputKey((previous) => previous + 1);
  };
  const requestRestore = (question: UnsentRequest) => {
    if (buildPayloadContent(prompt).trim()) setRestoreChoice(question);
    else restoreQuestion(question);
  };
  return {
    selectedModel,
    setSelectedModel,
    entries,
    baseline,
    persistentAdditional,
    prompt,
    inputKey,
    restoreChoice,
    missingSelectedYjCodes,
    targetState,
    handleAddBaseline,
    handleRemoveBaseline,
    handleClearBaseline,
    handleRemoveAdditional,
    handleClearAdditional,
    handleChangePrompt,
    handleSelectSuggestion,
    commitSent,
    requestRestore,
    cancelRestore: () => setRestoreChoice(null),
    confirmRestore: () => {
      if (restoreChoice) restoreQuestion(restoreChoice);
    },
  };
}
