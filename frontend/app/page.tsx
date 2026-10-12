"use client";

import Link from "next/link";
import { useState } from "react";
import { ChatHeader } from "./components/ChatHeader";
import { ChatInputForm } from "./components/ChatInputForm";
import { MedicineSelector } from "./components/MedicineSelector";
import { MessageList } from "./components/MessageList";
import { useChatWebSocket } from "./hooks/useChatWebSocket";
import { useMedicineCatalog } from "./hooks/useMedicineCatalog";
import type { MedicineEntry } from "./lib/medicineAutocomplete";

export default function Chat() {
  const [selectedModel, setSelectedModel] = useState("openai:gpt-6-luna");

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

  return (
    <div className="container">
      <Link href="/imports">添付文書XMLを取り込む</Link>
      <ChatHeader
        selectedModel={selectedModel}
        onModelChange={setSelectedModel}
        status={status}
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

      <MessageList messages={messages} isStreaming={isStreaming} />

      <ChatInputForm
        input={input}
        onChangeInput={setInput}
        onSubmit={sendMessage}
        onSelectMedicine={handleSelectMedicine}
        selectedYjCodes={selectedYjCodes}
        status={status}
        isStreaming={isStreaming}
      />
    </div>
  );
}
