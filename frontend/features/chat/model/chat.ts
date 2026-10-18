import type { JevResponseData } from "./jev";

export interface SourceReference {
  kind?: string;
  target_section_code?: string | null;
  target_url?: string | null;
  target_xml_id?: string | null;
}

export type DetectionSource = "logic" | "jev" | "keyword";

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

export const AVAILABLE_MODELS: ModelOption[] = [
  { value: "openai:gpt-6-luna", label: "OpenAI (GPT-6 Luna)" },
  { value: "openai:gpt-5.6-luna", label: "OpenAI (GPT-5.6 Luna)" },
  { value: "gemini:gemini-3.8-flash", label: "Google (Gemini 3.8 Flash)" },
];

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
