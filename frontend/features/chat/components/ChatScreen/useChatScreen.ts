import { type ComponentProps, useCallback } from "react";
import type { PromptDocument } from "../../../../shared/component/TokenPromptInput/PromptDocument";
import { useMobileLayout } from "../../../../shared/hooks/useMobileLayout";
import { buildPayloadContent } from "../../../medicine-selection";
import { useChatScroll } from "../../hooks/useChatScroll";
import { useChatWebSocket } from "../../hooks/useChatWebSocket";
import { useEvidencePanelState } from "../../hooks/useEvidencePanelState";
import type { ChatHeader } from "../ChatHeader";
import type { ChatScreenViewProps } from "./ChatScreenView";
import { useChatDraft } from "./useChatDraft";
/** Connects one transport subscription to the draft and evidence presentation. */
export function useChatScreen(): Omit<ChatScreenViewProps, "header"> & {
  header: ComponentProps<typeof ChatHeader>;
} {
  const isMobile = useMobileLayout();
  const { messageListRef, scrollToLatestUserMessage } = useChatScroll();
  const draft = useChatDraft();
  const {
    selectedModel,
    entries,
    baseline,
    persistentAdditional,
    targetState,
    commitSent,
  } = draft;
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
    (promptVal: PromptDocument) => {
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
        commitSent();

        scrollToLatestUserMessage();
      }
    },
    [
      targetState,
      isStreaming,
      selectedModel,
      sendMessage,
      scrollToLatestUserMessage,
      commitSent,
    ],
  );

  return {
    header: { selectedModel, onModelChange: draft.setSelectedModel, status },
    conversation: {
      messages,
      isStreaming,
      containerRef: messageListRef,
      openEvidenceIndex,
      evidencePaneTab,
      onToggleEvidence: handleToggleEvidence,
      onSelectSuggestion: draft.handleSelectSuggestion,
    },
    missingSelectedYjCodes: draft.missingSelectedYjCodes,
    delivery: {
      pending,
      unsent,
      restoreChoice: draft.restoreChoice,
      onCancelPending: cancelPending,
      onEdit: draft.requestRestore,
      onKeepDraft: draft.cancelRestore,
      onReplaceDraft: draft.confirmRestore,
    },
    inputKey: draft.inputKey,
    input: {
      baseline,
      onAddBaseline: draft.handleAddBaseline,
      onRemoveBaseline: draft.handleRemoveBaseline,
      onClearBaseline: draft.handleClearBaseline,
      additional: targetState.additional,
      onRemoveAdditional: draft.handleRemoveAdditional,
      onClearAdditional: draft.handleClearAdditional,
      prompt: draft.prompt,
      onChangePrompt: draft.handleChangePrompt,
      onSubmit: handleSendMessage,
      medicineEntries: entries,
      status,
      isStreaming,
      isStopping,
      showSetupHint: messages.length === 0,
      onAbort: abortRequest,
      canSend: targetState.canSend && !pending,
    },
    evidenceKey: `evidence-${openEvidenceIndex}`,
    evidence:
      showEvidencePane && activeEvidenceMessage
        ? {
            isMobile,
            sources: activeEvidenceMessage.sources || [],
            retrievalStatus: activeEvidenceMessage.retrievalStatus,
            jevResponse: activeEvidenceMessage.jevResponse,
            activeTab: evidencePaneTab,
            onTabChange: setEvidencePaneTab,
            onClose: closeEvidence,
            highlightWords: evidenceHighlightWords,
          }
        : null,
  };
}
