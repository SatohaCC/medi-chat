/** Application-owned editor snapshot. Native caret and selection stay in the UI adapter. */
export type PromptToken =
  | { type: "url"; url: string }
  | { type: "custom"; anchor: string; valueType: string; data: unknown }
  | {
      type: "placeholder";
      placeholderType: "token";
      anchor: string;
      valueType: string | null;
    }
  | { type: "placeholder"; placeholderType: "text" }
  | { type: "anchor"; valueType: string };
export type PromptSegment =
  | { type: "text"; text: string }
  | { type: "token"; text: string; value?: PromptToken };
export class PromptDocument {
  readonly segments: readonly PromptSegment[];
  constructor(segments: readonly PromptSegment[]) {
    this.segments = segments.map((segment) => ({ ...segment }));
  }
}
