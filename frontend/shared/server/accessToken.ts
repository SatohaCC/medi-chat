// Server-only: imported by proxy, never by client components.
import { createHash, createHmac, randomBytes, timingSafeEqual } from "node:crypto";

export const ACCESS_COOKIE = "medi_chat_access";
export const ACCESS_TTL = 30 * 86400;

export function accessSecret(): string | undefined {
  const secret = process.env.APP_SECRET_KEY || "";
  if (!secret && process.env.VERCEL !== "1" && process.env.NODE_ENV !== "production")
    return undefined;
  const length = Buffer.byteLength(secret, "utf8");
  if (length < 32 || length > 1024 || !secret.trim()) {
    throw new Error("APP_SECRET_KEY is not configured");
  }
  return secret;
}

export function matchesAccessKey(candidate: string, secret: string): boolean {
  return timingSafeEqual(
    createHash("sha256").update(candidate).digest(),
    createHash("sha256").update(secret).digest(),
  );
}

export function createAccessToken(
  secret: string,
  now = Math.floor(Date.now() / 1000),
): string {
  const unsigned = `v1.${now + ACCESS_TTL}.${randomBytes(16).toString("hex")}`;
  return `${unsigned}.${createHmac("sha256", secret).update(`medi-chat-access:${unsigned}`).digest("hex")}`;
}

export function validAccessToken(
  token: string | undefined,
  secret: string,
  now = Math.floor(Date.now() / 1000),
): boolean {
  const match = token?.match(/^v1\.([0-9]{1,12})\.([0-9a-f]{32})\.([0-9a-f]{64})$/);
  if (!match || match[0] !== token) return false;
  const expires = Number(match[1]);
  if (expires <= now || expires > now + ACCESS_TTL + 60) return false;
  const unsigned = `v1.${match[1]}.${match[2]}`;
  const expected = createHmac("sha256", secret)
    .update(`medi-chat-access:${unsigned}`)
    .digest();
  return timingSafeEqual(expected, Buffer.from(match[3], "hex"));
}
