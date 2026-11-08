import * as stylex from "@stylexjs/stylex";
import type { JevResponseData } from "../../model/jev";
import { JEV_INTENT_META } from "../../model/jevIntentMeta";
import { styles } from "./JevResponseInspector.styles";
export function JevIntentHeading({ response }: { response: JevResponseData }) {
  const intentAnswer = response.answers?.intent;
  const choice = intentAnswer?.choice;
  const confidence = intentAnswer?.confidence;
  const meta = choice ? JEV_INTENT_META[choice] : null;

  return (
    <div {...stylex.props(styles.titleRow)}>
      <span>質問の意図判定</span>
      {choice && (
        <span {...stylex.props(styles.intentBadge)}>
          {meta ? `${meta.label} (${choice})` : choice}
        </span>
      )}
      {response.qualifying_intents && response.qualifying_intents.length > 1 && (
        <span {...stylex.props(styles.multipleIntents)}>
          複数の観点:{" "}
          {response.qualifying_intents
            .map((k) => JEV_INTENT_META[k]?.label || k)
            .join(" ＋ ")}
        </span>
      )}
      {confidence !== undefined && (
        <span {...stylex.props(styles.confidencePill)}>
          確信度: {Math.round(confidence * 100)}%
        </span>
      )}
      {response.model && (
        <span {...stylex.props(styles.modelLabel)}>{response.model}</span>
      )}
      {response.error && <span {...stylex.props(styles.errorBadge)}>⚠️ エラー</span>}
    </div>
  );
}
