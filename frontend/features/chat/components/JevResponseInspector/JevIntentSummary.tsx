import * as stylex from "@stylexjs/stylex";
import type { JevResponseData } from "../../model/jev";
import { JEV_INTENT_META } from "../../model/jevIntentMeta";
import { JevProbabilityDistribution } from "./JevProbabilityDistribution";
import { styles } from "./JevResponseInspector.styles";
export function JevIntentSummary({
  response,
  showAllProbabilities,
  onToggleProbabilities,
}: {
  response: JevResponseData;
  showAllProbabilities: boolean;
  onToggleProbabilities: () => void;
}) {
  const intentAnswer = response.answers?.intent;
  const choice = intentAnswer?.choice;
  const confidence = intentAnswer?.confidence;
  const probabilities = intentAnswer?.probabilities;
  const meta = choice ? JEV_INTENT_META[choice] : null;

  return (
    <div {...stylex.props(styles.summaryPanel)}>
      {choice && (
        <div {...stylex.props(styles.chosenIntent)}>
          <div {...stylex.props(styles.intentHeading)}>質問から読み取った内容:</div>
          <div {...stylex.props(styles.choiceRow)}>
            <span {...stylex.props(styles.choiceLabel)}>{meta?.label || choice}</span>
            <span {...stylex.props(styles.choiceCode)}>({choice})</span>
            {confidence !== undefined && confidence >= 0.2 && (
              <span {...stylex.props(styles.targetBadge)}>[対象]</span>
            )}
          </div>
          {meta?.desc && (
            <div {...stylex.props(styles.intentDescription)}>{meta.desc}</div>
          )}
        </div>
      )}

      {confidence !== undefined && (
        <div {...stylex.props(styles.confidenceBlock)}>
          <div {...stylex.props(styles.confidenceHeading)}>
            <span {...stylex.props(styles.mutedLabel)}>確信度 (Confidence):</span>
            <span {...stylex.props(styles.confidenceValue)}>
              {(confidence * 100).toFixed(1)}% ({confidence.toFixed(2)})
            </span>
          </div>
          <div {...stylex.props(styles.probContainer)} data-probability-track="true">
            <div
              data-confidence-meter="true"
              {...stylex.props(
                styles.probBar,
                styles.confidenceWidth(
                  `${Math.min(Math.max(confidence * 100, 0), 100)}%`,
                ),
              )}
              data-probability-bar="true"
            />
          </div>
        </div>
      )}

      {response.qualifying_intents && response.qualifying_intents.length > 1 && (
        <div {...stylex.props(styles.multipleBlock)}>
          <div {...stylex.props(styles.multipleHeading)}>
            <span {...stylex.props(styles.multipleTitle)}>
              <span>⚡ マルチセクション取得（閾値20%以上）</span>
            </span>
            <span {...stylex.props(styles.modeLabel)}>
              {response.qualifying_intents.length}項目を統合取得
            </span>
          </div>
          <div {...stylex.props(styles.multipleDescription)}>
            確率20%以上の複数セクションを検出し、添付文書の該当箇所を網羅して検索・引用しました:
          </div>
          <div {...stylex.props(styles.qualifyingItems)}>
            {response.qualifying_intents.map((intentKey) => {
              const prob = probabilities?.[intentKey];
              const probPct = prob !== undefined ? `${(prob * 100).toFixed(1)}%` : null;
              const itemMeta = JEV_INTENT_META[intentKey];
              return (
                <div key={intentKey} {...stylex.props(styles.qualifyingItem)}>
                  <span {...stylex.props(styles.qualifyingName)}>
                    {itemMeta?.label || intentKey}
                  </span>
                  {probPct && (
                    <span {...stylex.props(styles.qualifyingPercentage)}>{probPct}</span>
                  )}
                  <span {...stylex.props(styles.qualifyingBadge)}>[対象]</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <JevProbabilityDistribution
        response={response}
        showAllProbabilities={showAllProbabilities}
        onToggle={onToggleProbabilities}
      />

      <div {...stylex.props(styles.meta, styles.metaBorder)}>
        {response.model && <div>モデル: {response.model}</div>}
        {response.request_id && <div>リクエストID: {response.request_id}</div>}
        {response.usage && (
          <div>
            トークン: 入力 {response.usage.input_tokens ?? 0} / 出力{" "}
            {response.usage.output_tokens ?? 0}
          </div>
        )}
      </div>
    </div>
  );
}
