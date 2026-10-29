"use client";

import { PromptFieldValue } from "@react-spectrum/ai";
import { Button } from "@react-spectrum/s2/Button";
import * as stylex from "@stylexjs/stylex";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useMobileLayout } from "../../../shared/hooks/useMobileLayout";
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
import { useEvidencePanelState } from "../hooks/useEvidencePanelState";
import type { UnsentRequest } from "../model/chatRequestLifecycle";
import { ChatHeader } from "./ChatHeader";
import { ChatInputForm } from "./ChatInputForm";
import { MessageList } from "./MessageList";
import { SourceEvidencePanel } from "./SourceEvidencePanel";

export function ChatScreen() {
  const isMobile = useMobileLayout();
  const [selectedModel, setSelectedModel] = useState("openai:gpt-6-luna");
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
  const [restoreChoice, setRestoreChoice] = useState<UnsentRequest | null>(null);

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

  const {
    messages,
    isStreaming,
    isStopping,
    abortRequest,
    pending,
    unsent,
    cancelPending,
    status,
    sendMessage,
  } = useChatWebSocket({
    selectedModel,
  });

  const {
    openEvidenceIndex,
    evidencePaneTab,
    setEvidencePaneTab,
    handleToggleEvidence,
    closeEvidence,
    activeEvidenceMessage,
    showEvidencePane,
    evidenceHighlightWords,
  } = useEvidencePanelState({
    autoOpen: !isMobile,
    messages,
    entries,
    baseline,
    persistentAdditional,
  });

  const handleSendMessage = useCallback(
    (promptVal: PromptFieldValue) => {
      const content = buildPayloadContent(promptVal).trim();
      if (!content || !targetState.canSend || isStreaming) {
        return;
      }

      const result = sendMessage({
        content,
        productYjCodes: targetState.target.map((m) => m.yj_code),
        context: {
          promptSegments: promptVal.segments,
          targets: targetState.target,
          model: selectedModel,
        },
      });

      if (result.ok) {
        const postState = resolvePostSendState(targetState);
        setPersistentAdditional(postState.persistentAdditional);
        setPrompt(new PromptFieldValue([]));
        setInputKey((prev) => prev + 1);

        scrollToLatestUserMessage();
      }
    },
    [targetState, isStreaming, selectedModel, sendMessage, scrollToLatestUserMessage],
  );

  const restoreQuestion = (question: UnsentRequest) => {
    if (!question.context) return;
    setPrompt(new PromptFieldValue([...question.context.promptSegments]));
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

          {pending && (
            <section aria-label="未送信の保留">
              <p role="status">未送信・接続待ちの保留: {pending.content}</p>
              <p>
                {pending.context?.targets.map((medicine) => medicine.name).join("、")} /{" "}
                {pending.context?.model}
              </p>
              <Button
                variant="secondary"
                onPress={() => cancelPending(pending.payload.request_id)}
              >
                保留を取消
              </Button>
            </section>
          )}
          {unsent.map((question) => (
            <section key={question.payload.request_id} aria-label="未送信の質問">
              <p>
                {question.reason === "expired"
                  ? "期限切れ"
                  : question.reason === "cancelled"
                    ? "取消"
                    : "認証により取消"}
                : {question.content}
              </p>
              <p>
                {question.context?.targets.map((medicine) => medicine.name).join("、")} /{" "}
                {question.context?.model}
              </p>
              <Button
                variant="secondary"
                onPress={() => {
                  if (buildPayloadContent(prompt).trim()) setRestoreChoice(question);
                  else restoreQuestion(question);
                }}
              >
                再編集
              </Button>
            </section>
          ))}
          {restoreChoice && (
            <section aria-label="再編集の確認">
              <p>別の質問を編集中です。</p>
              <Button variant="secondary" onPress={() => setRestoreChoice(null)}>
                現在の入力を保持
              </Button>
              <Button variant="secondary" onPress={() => restoreQuestion(restoreChoice)}>
                元の質問に置換
              </Button>
            </section>
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
            isStopping={isStopping}
            onAbort={abortRequest}
            canSend={targetState.canSend && !pending}
          />
        </div>

        {showEvidencePane && activeEvidenceMessage && (
          <SourceEvidencePanel
            isMobile={isMobile}
            key={`evidence-${openEvidenceIndex}`}
            sources={activeEvidenceMessage.sources || []}
            retrievalStatus={activeEvidenceMessage.retrievalStatus}
            jevResponse={activeEvidenceMessage.jevResponse}
            activeTab={evidencePaneTab}
            onTabChange={setEvidencePaneTab}
            onClose={closeEvidence}
            highlightWords={evidenceHighlightWords}
          />
        )}
      </div>
    </div>
  );
}
