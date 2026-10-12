"use client";
import * as stylex from "@stylexjs/stylex";
import Link from "next/link";
import { useRef, useState } from "react";
import { styles as layout } from "../../../shared/ui/PageLayout.styles";
import type { MedicineEntry } from "../../medicine-selection";
import { MedicineSelector, useMedicineCatalog } from "../../medicine-selection";
import { useChatWebSocket } from "../hooks/useChatWebSocket";
import { ChatHeader } from "./ChatHeader";
import { ChatInputForm } from "./ChatInputForm";
import { MessageList } from "./MessageList";

export function ChatScreen() {
  const [selectedModel, setSelectedModel] = useState("openai:gpt-6-luna");
  const messageListRef = useRef<HTMLElement | null>(null);

  const {
    selectedYjCodes,
    missingSelectedYjCodes,
    medicineOptions,
    medicineCatalogStatus,
    customMedicines,
    toggleYjCode,
    handleSelectMedicineFromAutocomplete,
  } = useMedicineCatalog("3339003F5020");

  const { messages, input, setInput, isStreaming, status, sendMessage } =
    useChatWebSocket({
      selectedModel,
      selectedYjCodes,
    });

  const handleSelectMedicine = (medicine: MedicineEntry) => {
    handleSelectMedicineFromAutocomplete(medicine, input);
  };

  const handleSendMessage = (e?: React.FormEvent) => {
    if (!input.trim() || selectedYjCodes.length === 0 || isStreaming) {
      sendMessage(e);
      return;
    }
    sendMessage(e);
    requestAnimationFrame(() => {
      const container = messageListRef.current;
      if (!container) return;
      const userMessages = container.querySelectorAll<HTMLElement>(
        '[data-message-role="user"]',
      );
      const latestUserMessage = userMessages[userMessages.length - 1];
      if (latestUserMessage) {
        const prefersReducedMotion =
          typeof window !== "undefined" &&
          window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        const containerRect = container.getBoundingClientRect();
        const messageRect = latestUserMessage.getBoundingClientRect();
        const targetScrollTop = Math.max(
          0,
          container.scrollTop + (messageRect.top - containerRect.top) - 20,
        );
        container.scrollTo({
          top: targetScrollTop,
          behavior: prefersReducedMotion ? "auto" : "smooth",
        });
      }
    });
  };

  return (
    <div {...stylex.props(layout.root)} data-screen="chat">
      <div style={{ display: "flex", gap: "16px", padding: "8px 20px" }}>
        <Link href="/search">キーワード検索</Link>
        <Link href="/imports">添付文書XMLを取り込む</Link>
      </div>
      <ChatHeader
        selectedModel={selectedModel}
        onModelChange={setSelectedModel}
        status={status}
      />

      <MessageList
        messages={messages}
        isStreaming={isStreaming}
        containerRef={messageListRef}
      />

      {missingSelectedYjCodes.length > 0 && (
        <p role="alert" aria-label="選択YJの消失">
          選択したYJコードが現在の候補にありません: {missingSelectedYjCodes.join(", ")}
          。別の薬へ自動変更していません。
        </p>
      )}
      <MedicineSelector
        medicineOptions={medicineOptions}
        medicineCatalogStatus={medicineCatalogStatus}
        selectedYjCodes={selectedYjCodes}
        customMedicines={customMedicines}
        onToggleYjCode={toggleYjCode}
      />

      <ChatInputForm
        input={input}
        onChangeInput={setInput}
        onSubmit={handleSendMessage}
        onSelectMedicine={handleSelectMedicine}
        selectedYjCodes={selectedYjCodes}
        status={status}
        isStreaming={isStreaming}
      />
    </div>
  );
}
