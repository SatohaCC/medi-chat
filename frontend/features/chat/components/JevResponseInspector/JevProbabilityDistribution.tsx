import * as stylex from "@stylexjs/stylex";
import { ActionButton as Button } from "../../../../shared/component/ActionButton";
import type { JevResponseData } from "../../model/jev";
import { JEV_INTENT_META } from "../../model/jevIntentMeta";
import { styles } from "./JevResponseInspector.styles";
export function JevProbabilityDistribution({
  response,
  showAllProbabilities,
  onToggle,
}: {
  response: JevResponseData;
  showAllProbabilities: boolean;
  onToggle: () => void;
}) {
  const choice = response.answers?.intent?.choice;
  const probabilities = response.answers?.intent?.probabilities;
  const allSortedProbabilities = probabilities
    ? Object.entries(probabilities).sort(([, a], [, b]) => b - a)
    : [];

  const displayedProbabilities = showAllProbabilities
    ? allSortedProbabilities
    : allSortedProbabilities.slice(0, 8);

  return (
    <>
      {allSortedProbabilities.length > 0 && (
        <div {...stylex.props(styles.probabilityList)}>
          <div {...stylex.props(styles.probabilityHeading)}>
            <span>
              候補項目と確率分布 (
              {showAllProbabilities
                ? `全${allSortedProbabilities.length}項目`
                : `上位${displayedProbabilities.length}項目`}
              ):
            </span>
            {allSortedProbabilities.length > 8 && (
              <Button appearance="text" onActivate={onToggle}>
                {showAllProbabilities
                  ? "上位8件に戻す"
                  : `全${allSortedProbabilities.length}件を表示`}
              </Button>
            )}
          </div>
          {displayedProbabilities.map(([key, prob]) => {
            const probPct = (prob * 100).toFixed(1);
            const itemMeta = JEV_INTENT_META[key];
            const isWinner = key === choice;
            const isQualifying =
              (response.qualifying_intents?.includes(key) ?? false) || prob >= 0.2;
            return (
              <div
                key={key}
                {...stylex.props(styles.probRow)}
                data-probability-row="true"
              >
                <span
                  {...stylex.props(
                    styles.probabilityItemLabel(
                      isWinner ? "#4c1d95" : isQualifying ? "#0e7490" : "var(--fg)",
                      isWinner || isQualifying ? 600 : 400,
                    ),
                  )}
                  title={itemMeta?.label || key}
                >
                  {itemMeta?.label || key}
                  {isQualifying && (
                    <span
                      {...stylex.props(
                        styles.probabilityBadge(
                          isWinner ? "#5b21b6" : "#0e7490",
                          isWinner
                            ? "rgba(124, 58, 237, 0.08)"
                            : "rgba(14, 116, 144, 0.08)",
                          isWinner
                            ? "rgba(124, 58, 237, 0.25)"
                            : "rgba(14, 116, 144, 0.25)",
                        ),
                      )}
                    >
                      [対象]
                    </span>
                  )}
                </span>
                <div
                  {...stylex.props(styles.probContainer)}
                  data-probability-track="true"
                >
                  <div
                    {...stylex.props(
                      styles.probBar,
                      styles.probabilityBarValue(
                        `${Math.min(Math.max(prob * 100, 0), 100)}%`,
                        isWinner
                          ? "linear-gradient(90deg, #7c3aed, #0284c7)"
                          : isQualifying
                            ? "linear-gradient(90deg, #0e7490, #0284c7)"
                            : "none",
                      ),
                    )}
                    data-probability-bar="true"
                  />
                </div>
                <span
                  {...stylex.props(
                    styles.probabilityPercentage(
                      isWinner ? "#047857" : isQualifying ? "#0e7490" : "var(--muted)",
                      isWinner || isQualifying ? 600 : 400,
                    ),
                  )}
                >
                  {probPct}%
                </span>
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
