const { transformSync } = require("next/dist/build/swc");
const babel = require("next/dist/compiled/babel/core");
const config = require("../babel.config.js");

module.exports = function transpile(source) {
  // Type checking belongs to tsc; transpilation must not depend on the TS 5 API.
  const javascript = transformSync(source, {
    filename: this.resourcePath,
    jsc: {
      parser: { syntax: "typescript", tsx: this.resourcePath.endsWith(".tsx") },
      target: "es2022",
      transform: { react: { runtime: "automatic" } },
    },
    module: { type: "es6" },
  }).code;
  return babel.transformSync(javascript, {
    filename: this.resourcePath,
    cwd: require("node:path").resolve(__dirname, ".."),
    babelrc: false,
    configFile: false,
    plugins: config.plugins.map(([plugin, options]) => [
      require.resolve(plugin),
      { ...options, runtimeInjection: this.getOptions().runtimeInjection ?? true },
    ]),
  }).code;
};
