import type { JevResponseData } from "./jev";

export interface SourceReference {
  kind?: string;
  target_section_code?: string | null;
  target_url?: string | null;
  target_xml_id?: string | null;
}

export type DetectionSource = "always" | "logic" | "jev" | "keyword";

export interface SourceItem {
  unit_id: string;
  document_id: string;
  product_name: string;
  generic_name: string;
  product_yj_codes: string[];
  document_revision: {
    source_label?: string;
    year_month?: string;
    version?: string | null;
  };
  section: { code: string; title: string };
  kind: string;
  excerpt: string;
  columns?: Record<string, string> | null;
  references: SourceReference[];
  url: string;
  retrieved_by: DetectionSource[];
}

export type RetrievalStatus = "jev_searching" | "complete" | "unavailable";

export type ConnectionStatus = "connecting" | "connected" | "disconnected";

export interface Message {
  role: "user" | "assistant";
  content: string;
  isError?: boolean;
  isInterrupted?: boolean;
  sources?: SourceItem[];
  retrievalStatus?: RetrievalStatus;
  jevResponse?: JevResponseData | null;
  notices?: string[];
}

export interface ModelOption {
  value: string;
  label: string;
}

export const AVAILABLE_MODELS = [
  { value: "openai:gpt-6-luna", label: "OpenAI (GPT-6 Luna)" },
  { value: "openai:gpt-5.6-luna", label: "OpenAI (GPT-5.6 Luna)" },
  //   { value: "gemini:gemini-3.8-flash", label: "Google (Gemini 3.8 Flash)" },
] as const satisfies readonly ModelOption[];

export type AvailableModel = (typeof AVAILABLE_MODELS)[number]["value"];

export interface ParsedModelOption {
  provider: string;
  model: string;
}

/**
 * Safely parses a model identifier like "openai:gpt-6-luna" into provider and model components.
 */
export function parseModelOption(modelValue: string): ParsedModelOption {
  const delimiterIndex = modelValue.indexOf(":");
  if (delimiterIndex === -1) {
    return { provider: "", model: modelValue };
  }
  return {
    provider: modelValue.slice(0, delimiterIndex),
    model: modelValue.slice(delimiterIndex + 1),
  };
}

export interface WsClientHistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export type WsClientMessage = {
  type: "message";
  provider: string;
  model: string;
  product_yj_codes: string[];
  messages: WsClientHistoryMessage[];
};

/**
 * Helper to ensure exhaustiveness checking on discriminated unions at compile-time.
 */
export function assertNever(x: never): never {
  throw new Error(`Unexpected discriminated union member: ${JSON.stringify(x)}`);
}

export type WsServerMessage =
  | { type: "sources"; sources: SourceItem[] }
  | {
      type: "retrieval_status";
      stage: RetrievalStatus;
      jev_response?: JevResponseData | null;
    }
  | { type: "jev_response"; data: JevResponseData }
  | { type: "notices"; notices: string[] }
  | { type: "text_delta"; content: string }
  | { type: "text_done" }
  | { type: "error"; content: string };
