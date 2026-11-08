import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { loadTestComponent } from "../../../../scripts/load-test-component.mjs";

const { JevIntentSummary } = await loadTestComponent(
  fileURLToPath(new URL("./JevIntentSummary.tsx", import.meta.url)),
);
test("intent presentation preserves probabilities, unknown labels and exact metadata", () => {
  const probabilities = Object.fromEntries(
    Array.from({ length: 10 }, (_, index) => [`test_${index}`, index / 10]),
  );
  const response = {
    model: "test-model",
    request_id: "test-request",
    answers: { intent: { choice: "test_0", confidence: 0, probabilities } },
    qualifying_intents: ["test_0", "test_1"],
  };
  for (const expanded of [false, true]) {
    const html = renderToStaticMarkup(
      createElement(JevIntentSummary, {
        response,
        showAllProbabilities: expanded,
        onToggleProbabilities() {},
      }),
    );
    assert.equal(
      (html.match(/data-probability-row="true"/g) ?? []).length,
      expanded ? 10 : 8,
    );
    for (const text of ["test_0", "test-model", "test-request", "0.0% (0.00)"])
      assert.ok(html.includes(text), text);
  }
});
