import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { resolve } from "node:path";

const frontendRoot = resolve(__dirname, "../..");
const require = createRequire(resolve(frontendRoot, "package.json"));
let bundle: Promise<string> | undefined;

export function zeroSelectionBundle() {
  bundle ??= new Promise<string>((accept, reject) => {
    const bundled = require("next/dist/compiled/webpack/webpack");
    const output = resolve(frontendRoot, "../tmp/stylex-zero-harness");
    bundled.webpack(
      {
        mode: "development",
        target: "web",
        entry: resolve(frontendRoot, "e2e/harness/zero-selection.tsx"),
        output: { path: output, filename: "harness.js" },
        resolve: { extensions: [".tsx", ".ts", ".js"] },
        module: {
          rules: [
            {
              test: /\.tsx?$/,
              exclude: /node_modules/,
              use: resolve(frontendRoot, "scripts/harness-typescript-loader.cjs"),
            },
          ],
        },
        plugins: [
          new bundled.webpack.DefinePlugin({
            "process.env.NEXT_PUBLIC_API_URL": JSON.stringify(""),
            "process.env.NEXT_PUBLIC_WS_URL": JSON.stringify(
              "ws://127.0.0.1:3100/api/ws",
            ),
          }),
        ],
      },
      async (
        error: Error | null,
        stats: { hasErrors(): boolean; toString(): string },
      ) => {
        if (error || stats.hasErrors()) reject(error || new Error(stats.toString()));
        else accept(await readFile(resolve(output, "harness.js"), "utf8"));
      },
    );
  });
  return bundle;
}
