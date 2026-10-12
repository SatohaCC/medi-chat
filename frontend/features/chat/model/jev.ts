export interface JevAnswer {
  type?: string;
  choice?: string;
  confidence?: number;
  probabilities?: Record<string, number>;
}

export interface JevResponseData {
  model?: string;
  request_id?: string;
  usage?: {
    input_tokens?: number;
    output_tokens?: number;
    [key: string]: unknown;
  };
  answers?: Record<string, JevAnswer>;
  qualifying_intents?: string[];
  error?: string;
  [key: string]: unknown;
}
