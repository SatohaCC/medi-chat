import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import test from "node:test";
import {
  ACCESS_TTL,
  createAccessToken,
  matchesAccessKey,
  validAccessToken,
} from "./accessToken.ts";

const secret = "test-access-key-for-issue-29-only-123456";

test("tokens have an expiry and nonce, reveal no key, and reject tampering/rotation", () => {
  const token = createAccessToken(secret, 1000);
  assert.equal(validAccessToken(token, secret, 1001), true);
  assert.equal(validAccessToken(token, secret, 1000 + ACCESS_TTL), false);
  assert.equal(validAccessToken(token, "rotated-key", 1001), false);
  assert.equal(validAccessToken(`${token}\n`, secret, 1001), false);
  assert.equal(token.includes(secret), false);
  assert.notEqual(createAccessToken(secret, 1000), token);
  assert.equal(matchesAccessKey(secret, secret), true);
  assert.equal(matchesAccessKey("wrong", secret), false);
});

test("the shared token format matches the backend protocol", () => {
  const unsigned = `v1.4600.${"a".repeat(32)}`;
  const signature = createHmac("sha256", secret)
    .update(`medi-chat-access:${unsigned}`)
    .digest("hex");
  assert.equal(validAccessToken(`${unsigned}.${signature}`, secret, 1000), true);
  assert.equal(validAccessToken(`${unsigned}.${signature}`, secret, 4600), false);
});
