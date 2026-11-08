import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { loadTestComponent } from "../../../scripts/load-test-component.mjs";

const { ToggleButton } = await loadTestComponent(
  fileURLToPath(new URL("./ToggleButton.tsx", import.meta.url)),
);
test("selected controls expose their controlled accessible state", () => {
  for (const selected of [false, true]) {
    const toggle = renderToStaticMarkup(
      createElement(
        ToggleButton,
        { selected, onSelectedChange() {}, variant: "chip" },
        "Option",
      ),
    );
    assert.match(toggle, new RegExp(`aria-pressed="${selected}"`));
  }
});
