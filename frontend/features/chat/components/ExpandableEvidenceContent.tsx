"use client";

import * as stylex from "@stylexjs/stylex";
import { ChevronDown, ChevronUp } from "lucide-react";
import { type ReactNode, useEffect, useId, useMemo, useRef, useState } from "react";
import { styles } from "./ExpandableEvidenceContent.styles";
import { SourceEvidenceContent } from "./SourceEvidenceContent";

export interface ExpandableEvidenceContentProps {
  content: string;
  highlightWords?: string[];
  alwaysExpanded?: boolean;
  children?: ReactNode;
}

const COLLAPSED_HEIGHT = 150;
const OVERFLOW_MARGIN = 20;

function restoreFocusableElements(container: HTMLElement) {
  const clampedEls = container.querySelectorAll<HTMLElement>(
    '[data-hidden-by-clamp="true"]',
  );
  for (const el of clampedEls) {
    const orig = el.getAttribute("data-orig-tabindex");
    if (orig !== null) {
      el.setAttribute("tabindex", orig);
      el.removeAttribute("data-orig-tabindex");
    } else {
      el.removeAttribute("tabindex");
    }
    el.removeAttribute("data-hidden-by-clamp");
  }
}

export function ExpandableEvidenceContent({
  content,
  highlightWords,
  alwaysExpanded = false,
  children,
}: ExpandableEvidenceContentProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isClamped, setIsClamped] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const contentId = useId();

  useEffect(() => {
    if (alwaysExpanded) return;
    const el = containerRef.current;
    if (!el) return;

    const checkOverflow = () => {
      const hasOverflow = el.scrollHeight > COLLAPSED_HEIGHT + OVERFLOW_MARGIN;
      setIsClamped(hasOverflow);
    };

    checkOverflow();

    if (typeof ResizeObserver !== "undefined") {
      const ro = new ResizeObserver(checkOverflow);
      ro.observe(contentRef.current ?? el);
      return () => ro.disconnect();
    }
  }, [alwaysExpanded]);

  const hasKeywordMatch = useMemo(() => {
    if (!highlightWords || highlightWords.length === 0) return false;
    const valid = highlightWords.filter((w) => w.trim().length > 0);
    if (valid.length === 0) return false;
    const lowerContent = content.toLowerCase();
    return valid.some((w) => lowerContent.includes(w.toLowerCase()));
  }, [content, highlightWords]);

  const showClamping = isClamped && !isExpanded;

  // Manage keyboard accessibility: remove visually clipped descendants from tab order when collapsed
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const updateFocusableElements = () => {
      if (showClamping) {
        const containerRect = container.getBoundingClientRect();
        const focusable = container.querySelectorAll<HTMLElement>(
          'a[href], button, input, textarea, select, details, summary, [tabindex]:not([tabindex="-1"])',
        );
        for (const el of focusable) {
          const rect = el.getBoundingClientRect();
          // Clipped links, including footer references, must not receive keyboard focus.
          if (rect.bottom > containerRect.top + COLLAPSED_HEIGHT - 4) {
            if (!el.hasAttribute("data-hidden-by-clamp")) {
              const orig = el.getAttribute("tabindex");
              if (orig !== null) {
                el.setAttribute("data-orig-tabindex", orig);
              }
              el.setAttribute("data-hidden-by-clamp", "true");
              el.tabIndex = -1;
            }
          }
        }
      } else {
        restoreFocusableElements(container);
      }
    };
    updateFocusableElements();
    const observer =
      typeof ResizeObserver === "undefined"
        ? null
        : new ResizeObserver(updateFocusableElements);
    if (contentRef.current) observer?.observe(contentRef.current);
    const mutations = new MutationObserver(updateFocusableElements);
    mutations.observe(container, { childList: true, subtree: true });

    return () => {
      observer?.disconnect();
      mutations.disconnect();
      restoreFocusableElements(container);
    };
  }, [showClamping]);

  // Always expanded (e.g. Warning / Contraindication) bypasses clamping and accordion
  if (alwaysExpanded) {
    return (
      children ?? (
        <SourceEvidenceContent content={content} highlightWords={highlightWords} />
      )
    );
  }

  const handleToggle = () => {
    if (isExpanded) {
      setIsExpanded(false);
      containerRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } else {
      setIsExpanded(true);
    }
  };

  return (
    <div>
      <div
        id={contentId}
        ref={containerRef}
        onScroll={() => {
          if (showClamping && containerRef.current) {
            containerRef.current.scrollTop = 0;
          }
        }}
        {...stylex.props(styles.wrapper, showClamping ? styles.clamped : styles.expanded)}
      >
        <div ref={contentRef}>
          {children ?? (
            <SourceEvidenceContent content={content} highlightWords={highlightWords} />
          )}
        </div>
        {showClamping && <div {...stylex.props(styles.fadeOverlay)} aria-hidden="true" />}
      </div>

      {isClamped && (
        <div {...stylex.props(styles.buttonRow)}>
          <button
            type="button"
            onClick={handleToggle}
            aria-expanded={isExpanded}
            aria-controls={contentId}
            {...stylex.props(styles.toggleButton, isExpanded && styles.collapseButton)}
          >
            {isExpanded ? (
              <>
                <ChevronUp size={13} strokeWidth={2} />
                <span>折りたたむ</span>
              </>
            ) : (
              <>
                <ChevronDown size={13} strokeWidth={2} />
                <span>続きを読む</span>
                {hasKeywordMatch && (
                  <span {...stylex.props(styles.keywordBadge)}>キーワード該当あり</span>
                )}
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
