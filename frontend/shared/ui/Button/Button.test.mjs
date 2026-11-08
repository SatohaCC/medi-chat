import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { loadTestComponent } from "../../../scripts/load-test-component.mjs";

const { Button } = await loadTestComponent(
  fileURLToPath(new URL("./Button.tsx", import.meta.url)),
);

test("ordinary actions expose disabled state without selection semantics", () => {
  const action = renderToStaticMarkup(createElement(Button, { disabled: true }, "Save"));
  assert.match(action, /disabled/);
  assert.doesNotMatch(action, /aria-pressed/);
});
