import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { ESLint } from "eslint";
import test from "node:test";

const cwd = fileURLToPath(new URL("../", import.meta.url));
const eslint = new ESLint({
  cwd,
  overrideConfigFile: fileURLToPath(
    new URL("../eslint.stylex.config.mjs", import.meta.url),
  ),
});

test("StyleX lint parses typed source with the compiler API compatibility package", async () => {
  const [result] = await eslint.lintText(
    'import * as stylex from "@stylexjs/stylex";\n' +
      "const width: number = 1;\n" +
      'export const styles = stylex.create({ valid: { borderWidth: width, borderStyle: "solid" } });\n',
    { filePath: "styles/lint-probe.styles.ts" },
  );
  assert.equal(result.errorCount, 0, JSON.stringify(result.messages));
});

test("StyleX lint rejects unsupported style shorthands", async () => {
  const [result] = await eslint.lintText(
    'import * as stylex from "@stylexjs/stylex";\n' +
      'export const styles = stylex.create({ invalid: { border: "1px solid red" } });\n',
    { filePath: "styles/lint-probe.styles.ts" },
  );
  assert.ok(
    result.messages.some((message) => message.ruleId === "@stylexjs/valid-styles"),
  );
});
