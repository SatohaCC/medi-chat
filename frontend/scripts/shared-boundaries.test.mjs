import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import test from "node:test";
import { checkSharedBoundaries } from "./shared-boundaries.mjs";

function fixture(files, check) {
  const root = mkdtempSync(join(tmpdir(), "shared-boundaries-"));
  try {
    const all = {
      "tsconfig.json": JSON.stringify({
        compilerOptions: {
          moduleResolution: "bundler",
          module: "esnext",
          paths: { "@/*": ["./*"] },
        },
      }),
      ...files,
    };
    for (const [name, content] of Object.entries(all)) {
      const path = join(root, name);
      mkdirSync(dirname(path), { recursive: true });
      writeFileSync(path, content);
    }
    check(checkSharedBoundaries(root));
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

test("shared boundaries allow UI composition and dependencies from features", () => {
  fixture(
    {
      "shared/ui/Button.ts": 'export { Button } from "react-aria-components";',
      "shared/component/Toolbar.ts": 'export { Button } from "../ui/Button";',
      "features/example/Screen.ts":
        'export { Button } from "@/shared/component/Toolbar";',
    },
    (issues) => assert.deepEqual(issues, []),
  );
});

for (const statement of [
  'import type { Value } from "@/features/example/model";',
  'export type { Value } from "../../features/example/model";',
  'export const load = () => import("@/features/example/model");',
  'type Value = import("@/features/example/model").Value;',
  'import model = require("@/features/example/model");',
]) {
  test(`shared boundaries reject feature dependencies: ${statement}`, () => {
    fixture(
      {
        "shared/hooks/useExample.ts": statement,
        "features/example/model.ts": "export interface Value { id: string }",
      },
      (issues) =>
        assert.ok(issues.some((issue) => issue.includes("features/example/model.ts"))),
    );
  });
}

test("features cannot hide a UI bypass in a helper or library imports in a component", () => {
  fixture(
    {
      "features/example/Screen.ts": 'export * from "@/shared/hooks/bridge";',
      "shared/hooks/bridge.ts": 'export * from "../ui/Button";',
      "shared/ui/Button.ts": "export const Button = {};",
      "shared/component/Other.ts": 'import {Button} from "react-aria-components";',
    },
    (issues) => {
      assert.ok(issues.some((issue) => issue.includes("Feature UI bypass")));
      assert.ok(
        issues.some(
          (issue) =>
            issue.includes("shared/component/Other.ts") &&
            issue.includes("UI library imports"),
        ),
      );
    },
  );
});

test("shared boundaries trace barrels and transitive API access through hooks", () => {
  fixture(
    {
      "shared/component/Header.ts": 'export * from "../hooks/useData";',
      "shared/hooks/useData.ts": 'export * from "../api/barrel";',
      "shared/api/barrel.ts": 'export * from "./client";',
      "shared/api/client.ts": "export const client = {};",
    },
    (issues) =>
      assert.ok(
        issues.some((issue) =>
          issue.includes(
            "shared/component/Header.ts -> shared/hooks/useData.ts -> shared/api/barrel.ts",
          ),
        ),
      ),
  );
});

test("shared boundaries reject app, routing, reverse UI layers and library bypasses", () => {
  fixture(
    {
      "shared/ui/Button.ts": 'export * from "../component/Toolbar";',
      "shared/component/Toolbar.ts":
        'import { useRouter } from "next/navigation"; export * from "@/app/page";',
      "app/page.ts": "export const value = 1;",
      "features/example/Screen.ts": 'import { Button } from "@react-spectrum/s2/Button";',
    },
    (issues) => {
      assert.ok(
        issues.some((issue) =>
          issue.includes("shared/ui/Button.ts -> shared/component/Toolbar.ts"),
        ),
      );
      assert.ok(issues.some((issue) => issue.includes("app/page.ts")));
      assert.ok(issues.some((issue) => issue.includes("routing belongs")));
      assert.ok(issues.some((issue) => issue.includes("UI library imports")));
    },
  );
});

test("shared boundaries include JSON, CSS and routing hidden in a helper", () => {
  fixture(
    {
      "shared/component/Header.ts":
        'import "./theme.css"; import { useRoute } from "../hooks/useRoute"; import data from "@/features/example/data.json";',
      "shared/component/theme.css": '@import "../styles/theme.css";',
      "shared/styles/theme.css": '@import "../../features/example/theme.css";',
      "features/example/theme.css": ":root { color: red; }",
      "features/example/data.json": "{}",
      "shared/hooks/useRoute.ts":
        'export { usePathname as useRoute } from "next/navigation";',
    },
    (issues) => {
      assert.ok(issues.some((issue) => issue.includes("features/example/data.json")));
      assert.ok(issues.some((issue) => issue.includes("features/example/theme.css")));
      assert.ok(
        issues.some((issue) =>
          issue.includes(
            "shared/component/Header.ts -> shared/hooks/useRoute.ts -> next/navigation",
          ),
        ),
      );
    },
  );
});

test("production shared boundaries hold", () => {
  assert.deepEqual(checkSharedBoundaries(), []);
});

for (const statement of [
  'import { Button } from "@/shared/ui/Button";',
  'export { Button } from "../../shared/ui/Button";',
  'type Button = import("@/shared/ui/Button").Button;',
  'const load = () => import("@/shared/ui/Button");',
]) {
  test(`features cannot bypass component: ${statement}`, () => {
    fixture(
      {
        "features/example/Screen.ts": statement,
        "shared/ui/Button.ts": "export const Button = {};",
      },
      (issues) =>
        assert.ok(
          issues.some((issue) => issue.includes("Features must use shared/component")),
        ),
    );
  });
}
