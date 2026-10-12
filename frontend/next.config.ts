import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  distDir: process.env.MEDI_CHAT_NEXT_DIST_DIR || ".next",
  /* config options here */
  reactCompiler: true,
};

export default nextConfig;
