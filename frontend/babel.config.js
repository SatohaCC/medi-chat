module.exports = {
  presets: ["next/babel"],
  plugins: [
    [
      "@stylexjs/babel-plugin",
      {
        dev: process.env.NODE_ENV !== "production",
        runtimeInjection: false,
        enableInlinedConditionalMerge: true,
        treeshakeCompensation: true,
        unstable_moduleResolution: { type: "commonJS", rootDir: __dirname },
      },
    ],
  ],
};
