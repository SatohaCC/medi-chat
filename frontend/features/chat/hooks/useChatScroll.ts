import { useCallback, useRef } from "react";

/**
 * Hook to manage scroll positioning in the chat message list.
 */
export function useChatScroll() {
  const messageListRef = useRef<HTMLElement | null>(null);

  const scrollToLatestUserMessage = useCallback(() => {
    requestAnimationFrame(() => {
      const container = messageListRef.current;
      if (!container) return;

      const userMessages = container.querySelectorAll<HTMLElement>(
        '[data-message-role="user"]',
      );
      const latestUserMessage = userMessages[userMessages.length - 1];
      if (!latestUserMessage) return;

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
    });
  }, []);

  return {
    messageListRef,
    scrollToLatestUserMessage,
  };
}
