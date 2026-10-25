import { createRequire } from "node:module";
import { resolve } from "node:path";
import { readFileSync } from "node:fs";
const frontendRoot = process.cwd();
const frontendRequire = createRequire(resolve(frontendRoot, "package.json"));
export async function buildChatHookProvider() {
  const bundled = frontendRequire("next/dist/compiled/webpack/webpack");
  const output = resolve(frontendRoot, "../tmp/chat-hook-provider");
  await new Promise((accept, reject) => {
    const compiler = bundled.webpack(
      {
        mode: "development",
        target: "web",
        context: frontendRoot,
        entry: resolve(frontendRoot, "e2e/helpers/chat-hook-provider.tsx"),
        output: { path: output, filename: "harness.js" },
        resolve: { extensions: [".tsx", ".ts", ".js"] },
        plugins: [
          new bundled.webpack.DefinePlugin({
            "process.env.NEXT_PUBLIC_API_URL": JSON.stringify("http://127.0.0.1:3100"),
            "process.env.NEXT_PUBLIC_WS_URL": JSON.stringify(
              "ws://127.0.0.1:3100/api/ws",
            ),
          }),
        ],
        module: {
          rules: [
            {
              test: /\.tsx?$/,
              exclude: /node_modules/,
              use: {
                loader: resolve(frontendRoot, "scripts/harness-typescript-loader.cjs"),
                options: { runtimeInjection: false },
              },
            },
          ],
        },
      },
      (error, stats) =>
        compiler.close((closeError) =>
          error || closeError || stats.hasErrors()
            ? reject(error || closeError || new Error(stats.toString()))
            : accept(),
        ),
    );
  });
  return readFileSync(resolve(output, "harness.js"), "utf8");
}
