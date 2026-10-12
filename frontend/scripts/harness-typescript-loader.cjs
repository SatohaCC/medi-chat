const ts = require("typescript");
const babel = require("next/dist/compiled/babel/core");
const config = require("../babel.config.js");

module.exports = function transpile(source) {
  const javascript = ts.transpileModule(source, {
    compilerOptions: {
      jsx: ts.JsxEmit.ReactJSX,
      module: ts.ModuleKind.ESNext,
      target: ts.ScriptTarget.ES2022,
    },
    fileName: this.resourcePath,
  }).outputText;
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
