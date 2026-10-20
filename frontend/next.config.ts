import { createRequire } from "node:module";
import { resolve } from "node:path";
import type { NextConfig } from "next";

// Resolve Next's own env loader without adding another dependency.
const requireFromNext = createRequire(require.resolve("next/package.json"));
if (process.env.VERCEL !== "1" && process.env.PYTHON_DOTENV_DISABLED !== "1") {
  requireFromNext("@next/env").loadEnvConfig(
    resolve(__dirname, ".."),
    process.env.NODE_ENV === "development",
    console,
    true,
  );
}

const nextConfig: NextConfig = {
  distDir: process.env.MEDI_CHAT_NEXT_DIST_DIR || ".next",
  devIndicators: process.env.MEDI_CHAT_TEST_UI === "1" ? false : undefined,
  reactCompiler: true,
};

export default nextConfig;
