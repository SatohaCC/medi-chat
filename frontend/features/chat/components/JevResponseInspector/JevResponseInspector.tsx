"use client";
import * as stylex from "@stylexjs/stylex";
import { useState } from "react";
import { Disclosure } from "../../../../shared/component/Disclosure";
import { Tabs } from "../../../../shared/component/Tabs";
import type { JevResponseData } from "../../model/jev";
import { JevIntentHeading } from "./JevIntentHeading";
import { JevIntentSummary } from "./JevIntentSummary";
import { JevRawData } from "./JevRawData";
import { styles } from "./JevResponseInspector.styles";
export function JevResponseInspector({
  response,
  standalone = false,
}: {
  response: JevResponseData;
  standalone?: boolean;
}) {
  const [activeTab, setActiveTab] = useState<"summary" | "raw">("summary");

  const [showAllProbabilities, setShowAllProbabilities] = useState(false);
  const headerBadges = <JevIntentHeading response={response} />;

  const tabsContent = (
    <Tabs
      value={activeTab}
      onValueChange={(value) => setActiveTab(value as "summary" | "raw")}
      label="質問意図の判定内容を切り替え"
      items={[
        {
          id: "summary",
          title: "判定内容",
          content: (
            <JevIntentSummary
              response={response}
              showAllProbabilities={showAllProbabilities}
              onToggleProbabilities={() =>
                setShowAllProbabilities((previous) => !previous)
              }
            />
          ),
        },
        {
          id: "raw",
          title: "詳細データ (JSON)",
          content: <JevRawData response={response} />,
        },
      ]}
    />
  );

  if (standalone) {
    return (
      <div {...stylex.props(styles.standaloneWrapper)}>
        <div {...stylex.props(styles.standaloneHeader)}>{headerBadges}</div>
        <div {...stylex.props(styles.body, styles.standaloneBody)}>
          {response.error && (
            <div {...stylex.props(styles.errorBody)}>
              質問意図の判定を取得できませんでした: {response.error}
            </div>
          )}
          {tabsContent}
        </div>
      </div>
    );
  }

  return (
    <Disclosure
      variant="accent"
      title={
        <>
          {headerBadges}
          <span {...stylex.props(styles.expandHint)}>クリックで展開</span>
        </>
      }
    >
      <div {...stylex.props(styles.body)}>
        {response.error && (
          <div {...stylex.props(styles.errorBody)}>
            質問意図の判定を取得できませんでした: {response.error}
          </div>
        )}
        {tabsContent}
      </div>
    </Disclosure>
  );
}
