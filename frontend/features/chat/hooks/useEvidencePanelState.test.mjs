import assert from "node:assert/strict";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
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
