"use client";

import * as stylex from "@stylexjs/stylex";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { styles } from "./ExpandableEvidenceContent.styles";
import { SourceEvidenceContent } from "./SourceEvidenceContent";

export interface ExpandableEvidenceContentProps {
  content: string;
  highlightWords?: string[];
  alwaysExpanded?: boolean;
}

const COLLAPSED_HEIGHT = 150;
const OVERFLOW_MARGIN = 20;

export function ExpandableEvidenceContent({
  content,
  highlightWords,
  alwaysExpanded = false,
}: ExpandableEvidenceContentProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isClamped, setIsClamped] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (alwaysExpanded || !content) return;
    const el = containerRef.current;
    if (!el) return;

    const checkOverflow = () => {
      const hasOverflow = el.scrollHeight > COLLAPSED_HEIGHT + OVERFLOW_MARGIN;
      setIsClamped(hasOverflow);
    };

    checkOverflow();

    if (typeof ResizeObserver !== "undefined") {
      const ro = new ResizeObserver(checkOverflow);
      ro.observe(el);
      return () => ro.disconnect();
    }
  }, [alwaysExpanded, content]);

  const hasKeywordMatch = useMemo(() => {
    if (!highlightWords || highlightWords.length === 0) return false;
    const valid = highlightWords.filter((w) => w.trim().length > 0);
    if (valid.length === 0) return false;
    const lowerContent = content.toLowerCase();
    return valid.some((w) => lowerContent.includes(w.toLowerCase()));
  }, [content, highlightWords]);

  // Always expanded (e.g. Warning / Contraindication) bypasses clamping and accordion
  if (alwaysExpanded) {
    return (
      <SourceEvidenceContent content={content} highlightWords={highlightWords} />
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

  const showClamping = isClamped && !isExpanded;

  return (
    <div>
      <div
        ref={containerRef}
        {...stylex.props(
          styles.wrapper,
          showClamping ? styles.clamped : styles.expanded,
        )}
      >
        <SourceEvidenceContent content={content} highlightWords={highlightWords} />
        {showClamping && <div {...stylex.props(styles.fadeOverlay)} aria-hidden="true" />}
      </div>

      {isClamped && (
        <div {...stylex.props(styles.buttonRow)}>
          <button
            type="button"
            onClick={handleToggle}
            aria-expanded={isExpanded}
            {...stylex.props(
              styles.toggleButton,
              isExpanded && styles.collapseButton,
            )}
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
                  <span {...stylex.props(styles.keywordBadge)}>
                    キーワード該当あり
                  </span>
                )}
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
