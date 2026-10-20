import { resolve } from "node:path";
import type { NextConfig } from "next";

if (process.env.VERCEL !== "1" && process.env.PYTHON_DOTENV_DISABLED !== "1") {
  require(resolve(__dirname, "../scripts/root-environment.cjs")).loadRootEnvironment(
    resolve(__dirname, ".."),
  );
}

const nextConfig: NextConfig = {
  distDir: process.env.MEDI_CHAT_NEXT_DIST_DIR || ".next",
  devIndicators: process.env.MEDI_CHAT_TEST_UI === "1" ? false : undefined,
  reactCompiler: true,
};

export default nextConfig;
