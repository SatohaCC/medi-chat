import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import babelConfig from "./babel.config.js";

// Resolve from this configuration's runtime location. Turbopack's dev runtime
// may append the workspace subpath to the package root; require the real file.
let frontendRoot = dirname(fileURLToPath(import.meta.url));
while (!existsSync(join(frontendRoot, "postcss.config.mjs"))) {
  const parent = dirname(frontendRoot);
  if (parent === frontendRoot) throw new Error("Cannot locate frontend PostCSS config");
  frontendRoot = parent;
}

const config = {
  plugins: {
    "@stylexjs/postcss-plugin": {
      cwd: frontendRoot,
      include: [
        "app/**/*.{js,jsx,ts,tsx}",
        "features/**/*.{js,jsx,ts,tsx}",
        "shared/**/*.{js,jsx,ts,tsx}",
        "styles/**/*.{js,jsx,ts,tsx}",
      ].map((pattern) => join(frontendRoot, pattern).replaceAll("\\", "/")),
      babelConfig: {
        babelrc: false,
        parserOpts: { plugins: ["typescript", "jsx"] },
        plugins: babelConfig.plugins.map(([plugin, options]) => [
          plugin,
          {
            ...options,
            unstable_moduleResolution: {
              ...options.unstable_moduleResolution,
              rootDir: frontendRoot,
            },
          },
        ]),
      },
      useCSSLayers: true,
    },
  },
};

export default config;
