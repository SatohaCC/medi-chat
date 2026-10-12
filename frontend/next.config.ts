import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  distDir: process.env.MEDI_CHAT_NEXT_DIST_DIR || ".next",
  devIndicators: process.env.MEDI_CHAT_TEST_UI === "1" ? false : undefined,
  reactCompiler: true,
};

export default nextConfig;
