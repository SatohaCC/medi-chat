import type { StorybookConfig } from "@storybook/nextjs-vite";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import stylexPlugin from "@stylexjs/unplugin";

const currentDir = dirname(fileURLToPath(import.meta.url));
const frontendRoot = resolve(currentDir, "..");

const config: StorybookConfig = {
  stories: [
    "../features/**/*.stories.@(js|jsx|mjs|ts|tsx)",
  ],
  framework: {
    name: "@storybook/nextjs-vite",
    options: {},
  },
  async viteFinal(config) {
    config.plugins = config.plugins || [];
    config.plugins.push(
      stylexPlugin.vite({
        useCSSLayers: true,
        unstable_moduleResolution: {
          type: "commonJS",
          rootDir: frontendRoot,
        },
      }),
    );
    const babelHelperAlias = {
      find: /^@babel\/runtime\/helpers\/esm\/(.*)$/,
      replacement: "@babel/runtime/helpers/$1",
    };
    const babelRegeneratorAlias = {
      find: "@babel/runtime/regenerator",
      replacement: "@babel/runtime/helpers/regenerator",
    };
    if (Array.isArray(config.resolve?.alias)) {
      config.resolve.alias.push(babelHelperAlias, babelRegeneratorAlias, {
        find: "@",
        replacement: frontendRoot,
      });
    } else {
      config.resolve = config.resolve || {};
      config.resolve.alias = [
        babelHelperAlias,
        babelRegeneratorAlias,
        { find: "@", replacement: frontendRoot },
        ...Object.entries(config.resolve.alias || {}).map(([find, replacement]) => ({
          find,
          replacement,
        })),
      ];
    }
    return config;
  },
};

export default config;
