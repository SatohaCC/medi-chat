import assert from "node:assert/strict";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { createElement, useRef, useState } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { loadTestComponent } from "../../../scripts/load-test-component.mjs";

const { useEvidencePanelState } = await loadTestComponent(
  fileURLToPath(new URL("./useEvidencePanelState.ts", import.meta.url)),
);

function TestConsumer({ options, onRender }) {
  const state = useEvidencePanelState(options);
  if (onRender) onRender(state);
  return createElement(
    "div",
    {
      "data-open-index": state.openEvidenceIndex,
      "data-show-pane": state.showEvidencePane,
      "data-tab": state.evidencePaneTab,
    },
    state.showEvidencePane ? "open" : "closed",
  );
}

test("useEvidencePanelState: 根拠がない場合はパネルが自動で開かない", () => {
  let captured;
  const messages = [
    { role: "user", content: "質問" },
    { role: "assistant", content: "回答" },
  ];
  const html = renderToStaticMarkup(
    createElement(TestConsumer, {
      options: {
        messages,
        entries: [],
        baseline: [],
        persistentAdditional: [],
      },
      onRender: (s) => {
        captured = s;
      },
    }),
  );

  assert.equal(captured.showEvidencePane, false);
  assert.equal(captured.openEvidenceIndex, null);
  assert.match(html, /closed/);
});

test("useEvidencePanelState: アシスタントに根拠がある場合は最新メッセージで自動で開く", () => {
  let captured;
  const messages = [
    { role: "user", content: "質問" },
    {
      role: "assistant",
      content: "根拠付き回答",
      sources: [
        {
          unit_id: "u1",
          product_name: "薬A",
          excerpt: "効能効果",
        },
      ],
    },
  ];
  const html = renderToStaticMarkup(
    createElement(TestConsumer, {
      options: {
        messages,
        entries: [],
        baseline: [],
        persistentAdditional: [],
      },
      onRender: (s) => {
        captured = s;
      },
    }),
  );

  assert.equal(captured.showEvidencePane, true);
  assert.equal(captured.openEvidenceIndex, 1);
  assert.equal(captured.evidencePaneTab, "sources");
  assert.equal(captured.activeEvidenceMessage?.content, "根拠付き回答");
  assert.match(html, /open/);
});

test("useEvidencePanelState: 2件以上根拠がある際に過去の根拠を閉じても最新へ誤フォールバックせず閉じた状態を維持する", () => {
  let recordedResults;
  function InteractiveTest() {
    const messages = [
      { role: "user", content: "質問1" },
      { role: "assistant", content: "回答1", sources: [{ unit_id: "u1" }] },
      { role: "user", content: "質問2" },
      { role: "assistant", content: "回答2", sources: [{ unit_id: "u2" }] },
    ];
    const panel = useEvidencePanelState({
      messages,
      entries: [],
      baseline: [],
      persistentAdditional: [],
    });
    const [step, setStep] = useState(0);
    const results = useRef([]);

    if (step === 0) {
      results.current.push({ step: "initial", openIndex: panel.openEvidenceIndex });
      panel.handleToggleEvidence(1);
      setStep(1);
    } else if (step === 1) {
      results.current.push({ step: "opened_older", openIndex: panel.openEvidenceIndex });
      panel.closeEvidence();
      setStep(2);
    } else if (step === 2) {
      results.current.push({ step: "closed_older", openIndex: panel.openEvidenceIndex });
      recordedResults = results.current;
    }

    return createElement("div", null, String(panel.openEvidenceIndex));
  }

  renderToStaticMarkup(createElement(InteractiveTest));

  assert.ok(recordedResults, "結果が記録されていること");
  assert.equal(recordedResults[0].openIndex, 3, "初期状態は最新の回答2（index 3）が開く");
  assert.equal(recordedResults[1].openIndex, 1, "過去の回答1をクリックするとindex 1に切り替わる");
  assert.equal(
    recordedResults[2].openIndex,
    null,
    "過去の根拠を閉じた際、index 3へ誤って再展開されず null のまま閉じる",
  );
});

