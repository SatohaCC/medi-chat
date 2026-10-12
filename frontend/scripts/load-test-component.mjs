import { createRequire } from "node:module";
import { basename, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(resolve(frontendRoot, "package.json"));
export async function loadTestComponent(file) {
  const bundled = require("next/dist/compiled/webpack/webpack");
  const output = resolve(frontendRoot, "../tmp/stylex-node-components");
  const filename = `${basename(file, ".tsx")}.cjs`;
  await new Promise((accept, reject) => {
    bundled.webpack(
      {
        mode: "development",
        target: "node",
        context: frontendRoot,
        entry: file,
        output: { path: output, filename, library: { type: "commonjs2" } },
        resolve: { extensions: [".tsx", ".ts", ".js"] },
        externals: [
          ({ request }, callback) => {
            if (
              request &&
              !request.startsWith(".") &&
              !request.startsWith("/") &&
              !/^[A-Za-z]:/.test(request)
            ) {
              try {
                callback(null, `commonjs ${require.resolve(request)}`);
              } catch (error) {
                callback(error);
              }
            } else callback();
          },
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
        error || stats.hasErrors()
          ? reject(error || new Error(stats.toString()))
          : accept(),
    );
  });
  return require(resolve(output, filename));
}
