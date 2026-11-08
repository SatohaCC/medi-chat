"use client";

import * as stylex from "@stylexjs/stylex";
import { useCallback, useEffect, useMemo, useRef, useState, useTransition } from "react";
import { SpectrumButton as Button } from "../../ui/Button";
import {
  InsertTokenMenuItem,
  PromptField,
  PromptFieldValue,
  PromptTokenField,
} from "../../ui/PromptField";
import Send from "../../ui/SendIcon";
import Stop from "../../ui/StopIcon";
import { TokenFieldContext } from "../../ui/TokenField";
import { PromptDocument, type PromptToken } from "./PromptDocument";
import { styles } from "./TokenPromptInput.styles";

export interface CompletionOption {
  id: string;
  label: string;
  token: PromptToken;
}
const nativeValues = new WeakMap<PromptDocument, PromptFieldValue>();
function toDocument(value: PromptFieldValue): PromptDocument {
  const document = new PromptDocument(value.segments);
  nativeValues.set(document, value);
  return document;
}
function toNative(value: PromptDocument): PromptFieldValue {
  let native = nativeValues.get(value);
  if (!native) {
    native = new PromptFieldValue([...value.segments]);
    nativeValues.set(value, native);
  }
  return native;
}
export interface TokenPromptInputProps {
  maxLength: number;
  value: PromptDocument;
  onChange: (value: PromptDocument) => void;
  onSubmit: (prompt: PromptDocument) => void;
  searchCompletions: (query: string) => CompletionOption[];
  serialize: (value: PromptDocument) => string;
  accessibleLabel: string;
  placeholder: string;
  testId?: string;
  sendLabel: string;
  stopLabel: string;
  stoppingLabel: string;
  lengthError: string;
  isStreaming?: boolean;
  isStopping?: boolean;
  onAbort?: () => void;
  disabled?: boolean;
  canSend?: boolean;
}

export function TokenPromptInput({
  maxLength,
  value,
  onChange,
  onSubmit,
  searchCompletions,
  serialize,
  accessibleLabel,
  placeholder,
  testId,
  sendLabel,
  stopLabel,
  stoppingLabel,
  lengthError,
  isStreaming = false,
  isStopping = false,
  onAbort,
  disabled = false,
  canSend = true,
}: TokenPromptInputProps) {
  const nativeValue = useMemo(() => toNative(value), [value]);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [dismissedContent, setDismissedContent] = useState<string | null>(null);
  const content = serialize(value).trim();
  const tooLong = Array.from(content).length > maxLength;
  const blocked = disabled || isStreaming || !canSend || !content || tooLong;

  const [, startTransition] = useTransition();
  const [transitionQuery, setTransitionQuery] = useState("");
  const lastRequestedKeyRef = useRef<{
    query: string;
    search: (query: string) => CompletionOption[];
  }>({
    query: "",
    search: searchCompletions,
  });

  // Calculate search results in the rendering phase during transition, not in the synchronous startTransition callback
  const cachedResult = useMemo(() => {
    if (!transitionQuery.trim()) {
      return {
        query: transitionQuery,
        search: searchCompletions,
        matches: [] as CompletionOption[],
      };
    }
    return {
      query: transitionQuery,
      search: searchCompletions,
      matches: searchCompletions(transitionQuery),
    };
  }, [transitionQuery, searchCompletions]);

  useEffect(() => {
    if (containerRef.current) {
      const textbox = containerRef.current.querySelector('[role="textbox"]');
      if (textbox) {
        textbox.setAttribute("aria-label", accessibleLabel);
      }
    }
  }, [accessibleLabel]);

  const updateQueryTransition = useCallback(
    (query: string) => {
      if (
        lastRequestedKeyRef.current.query === query &&
        lastRequestedKeyRef.current.search === searchCompletions
      ) {
        return;
      }
      lastRequestedKeyRef.current = { query, search: searchCompletions };
      startTransition(() => {
        setTransitionQuery(query);
      });
    },
    [searchCompletions],
  );

  const renderCompletions = useCallback(
    (filterValue: string) => {
      if (dismissedContent === content) return null;
      const query = filterValue.replace(/^[@＠]/, "");
      if (!query.trim()) {
        return null;
      }

      if (
        lastRequestedKeyRef.current.query !== query ||
        lastRequestedKeyRef.current.search !== searchCompletions
      ) {
        queueMicrotask(() => {
          updateQueryTransition(query);
        });
      }

      // Ensure cached results belong to the current query and catalog to prevent showing stale mismatches
      let matches: CompletionOption[];
      if (cachedResult.query === query && cachedResult.search === searchCompletions) {
        matches = cachedResult.matches;
      } else {
        matches = searchCompletions(query);
      }

      if (matches.length === 0) {
        return null;
      }
      return matches.map((item) => (
        <InsertTokenMenuItem
          key={item.id}
          id={item.id}
          textValue={item.label}
          token={{ type: "token", text: item.label, value: item.token }}
        >
          {item.label}
        </InsertTokenMenuItem>
      ));
    },
    [dismissedContent, content, updateQueryTransition, cachedResult, searchCompletions],
  );

  const handleSubmit = useCallback(
    (promptVal: PromptFieldValue) => {
      if (blocked) return;
      onSubmit(toDocument(promptVal));
    },
    [blocked, onSubmit],
  );

  return (
    <div
      ref={containerRef}
      data-testid={testId}
      onKeyDownCapture={(event) => {
        if (event.key === "Escape" && !event.nativeEvent.isComposing)
          setDismissedContent(content);
      }}
    >
      <PromptField
        value={nativeValue}
        onChange={(next) => {
          const document = toDocument(next);
          if (serialize(document).trim() !== content) setDismissedContent(null);
          onChange(document);

          try {
            const anchor = next.findText(
              next.caretPosition,
              PromptFieldValue.Direction.Backward,
              /[@＠]/,
            );
            if (anchor != null) {
              const q = next
                .slice(anchor, next.caretPosition)
                .toString()
                .replace(/^[@＠]/, "");
              updateQueryTransition(q);
            } else {
              updateQueryTransition("");
            }
          } catch {
            // fallback handled by renderCompletions queueMicrotask
          }
        }}
        onSubmit={handleSubmit}
        isGenerating={isStreaming}
        aiDisclaimer=""
      >
        <TokenFieldContext.Provider value={{ isDisabled: disabled || isStreaming }}>
          <PromptTokenField
            completionTrigger={/[@＠]/}
            renderCompletions={renderCompletions}
            placeholder={placeholder}
          />
        </TokenFieldContext.Provider>
        <div {...stylex.props(styles.submit)}>
          <Button
            variant="primary"
            staticColor="auto"
            aria-label={
              isStreaming ? (isStopping ? stoppingLabel : stopLabel) : sendLabel
            }
            isDisabled={isStreaming ? isStopping : Boolean(blocked)}
            onPress={() => {
              if (isStreaming) {
                if (!isStopping) onAbort?.();
              } else handleSubmit(nativeValue);
            }}
          >
            {isStreaming ? <Stop /> : <Send />}
          </Button>
          {isStopping && <span role="status">{stoppingLabel}</span>}
        </div>
      </PromptField>
      {tooLong && <p role="alert">{lengthError}</p>}
    </div>
  );
}
