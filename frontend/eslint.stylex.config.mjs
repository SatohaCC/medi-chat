import stylex from "@stylexjs/eslint-plugin";
import tseslint from "typescript-eslint";

export default [
  {
    files: [
      "app/**/*.{ts,tsx}",
      "features/**/*.{ts,tsx}",
      "shared/**/*.{ts,tsx}",
      "styles/**/*.ts",
    ],
    languageOptions: { parser: tseslint.parser },
    plugins: { "@stylexjs": stylex },
    rules: {
      "@stylexjs/valid-styles": "error",
      "@stylexjs/valid-shorthands": "error",
      "@stylexjs/no-conflicting-props": "error",
      "@stylexjs/enforce-extension": "error",
    },
  },
];
