"use client";

import { PromptFieldValue } from "@react-spectrum/ai";
import * as stylex from "@stylexjs/stylex";
import { useCallback, useEffect, useMemo, useState } from "react";
import { styles as layout } from "../../../shared/ui/PageLayout.styles";
import {
  buildPayloadContent,
  computeTargetMedicines,
  extractMentionsFromSegments,
  resolvePostSendState,
  type SelectedMedicineItem,
  useMedicineEntries,
} from "../../medicine-selection";
import { useChatScroll } from "../hooks/useChatScroll";
import { useChatWebSocket } from "../hooks/useChatWebSocket";
import { extractHighlightWords } from "../model/highlightWords";
import { ChatHeader } from "./ChatHeader";
import { ChatInputForm } from "./ChatInputForm";
import { MessageList } from "./MessageList";
import { SourceEvidencePanel } from "./SourceEvidencePanel";

export function ChatScreen() {
  const [selectedModel, setSelectedModel] = useState("openai:gpt-6-luna");
  const [openEvidenceIndex, setOpenEvidenceIndex] = useState<number | null>(null);
  const { messageListRef, scrollToLatestUserMessage } = useChatScroll();

  const { entries, activeMedicines } = useMedicineEntries();

  // Baseline prescription: default 3339003F5020 (イグザレルト錠15mg)
  const defaultBaseline = useMemo<SelectedMedicineItem>(() => {
    const match = entries.find((item) => item.y === "3339003F5020");
    return {
      yj_code: "3339003F5020",
      name: match ? match.n : "イグザレルト錠15mg",
    };
  }, [entries]);

  const [baseline, setBaseline] = useState<SelectedMedicineItem[]>([defaultBaseline]);
  const [persistentAdditional, setPersistentAdditional] = useState<
    SelectedMedicineItem[]
  >([]);
  const [prompt, setPrompt] = useState<PromptFieldValue>(() => new PromptFieldValue([]));
  const [inputKey, setInputKey] = useState(0);

  // Sync default baseline name once catalog loads
  useEffect(() => {
    if (entries.length > 0) {
      setBaseline((prev) =>
        prev.map((item) => {
          if (item.yj_code === "3339003F5020" && item.name === "イグザレルト錠15mg") {
            const match = entries.find((m) => m.y === item.yj_code);
            if (match && match.n !== item.name) {
              return { ...item, name: match.n };
            }
          }
          return item;
        }),
      );
    }
  }, [entries]);

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

  const { messages, isStreaming, status, sendMessage } = useChatWebSocket({
    selectedModel,
  });

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

  const handleSendMessage = useCallback(
    (promptVal: PromptFieldValue) => {
      const content = buildPayloadContent(promptVal).trim();
      if (!content || !targetState.canSend || isStreaming) {
        return;
      }

      const result = sendMessage({
        content,
        productYjCodes: targetState.target.map((m) => m.yj_code),
      });

      if (result.ok) {
        const postState = resolvePostSendState(targetState);
        setPersistentAdditional(postState.persistentAdditional);
        setPrompt(new PromptFieldValue([]));
        setInputKey((prev) => prev + 1);

        scrollToLatestUserMessage();
      }
    },
    [targetState, isStreaming, sendMessage, scrollToLatestUserMessage],
  );

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
        setPrompt(new PromptFieldValue(remaining));
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
    setPrompt(new PromptFieldValue(remaining));
  }, [baseline, prompt]);

  const handleChangePrompt = useCallback((nextPrompt: PromptFieldValue) => {
    const newMentions = extractMentionsFromSegments(nextPrompt.segments);
    if (newMentions.length > 0) {
      setPersistentAdditional([]);
    }
    setPrompt(nextPrompt);
  }, []);

  const handleSelectSuggestion = useCallback((promptText: string) => {
    setPrompt(new PromptFieldValue([{ type: "text", text: promptText }]));
  }, []);

  return (
    <div {...stylex.props(layout.root)} data-screen="chat">
      <ChatHeader
        selectedModel={selectedModel}
        onModelChange={setSelectedModel}
        status={status}
      />

      <div {...stylex.props(layout.workspace)}>
        <div {...stylex.props(layout.chatColumn)}>
          <MessageList
            messages={messages}
            isStreaming={isStreaming}
            containerRef={messageListRef}
            openEvidenceIndex={openEvidenceIndex}
            evidencePaneTab={evidencePaneTab}
            onToggleEvidence={handleToggleEvidence}
            baseline={baseline}
            onSelectSuggestion={handleSelectSuggestion}
          />

          {missingSelectedYjCodes.length > 0 && (
            <p
              role="alert"
              aria-label="選択YJの消失"
              {...stylex.props(layout.missingAlert)}
            >
              選択したYJコードが現在の候補にありません:{" "}
              {missingSelectedYjCodes.join(", ")}
              。別の薬へ自動変更していません。
            </p>
          )}

          <ChatInputForm
            key={inputKey}
            baseline={baseline}
            onAddBaseline={handleAddBaseline}
            onRemoveBaseline={handleRemoveBaseline}
            onClearBaseline={handleClearBaseline}
            additional={targetState.additional}
            onRemoveAdditional={handleRemoveAdditional}
            onClearAdditional={handleClearAdditional}
            prompt={prompt}
            onChangePrompt={handleChangePrompt}
            onSubmit={handleSendMessage}
            medicineEntries={entries}
            status={status}
            isStreaming={isStreaming}
            canSend={targetState.canSend}
          />
        </div>

        {showEvidencePane && activeEvidenceMessage && (
          <SourceEvidencePanel
            key={`evidence-${openEvidenceIndex}`}
            sources={activeEvidenceMessage.sources || []}
            retrievalStatus={activeEvidenceMessage.retrievalStatus}
            jevResponse={activeEvidenceMessage.jevResponse}
            activeTab={evidencePaneTab}
            onTabChange={setEvidencePaneTab}
            onClose={() => setOpenEvidenceIndex(null)}
            highlightWords={evidenceHighlightWords}
          />
        )}
      </div>
    </div>
  );
}
