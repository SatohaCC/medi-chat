import { type NextRequest, NextResponse } from "next/server";
import {
  ACCESS_COOKIE,
  ACCESS_TTL,
  accessSecret,
  createAccessToken,
  matchesAccessKey,
  validAccessToken,
} from "./shared/server/accessToken";

const restricted =
  '<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>アクセス制限 | medi-chat</title><body><main><h1>アクセスが制限されています</h1><p>配布された専用リンクからアクセスしてください。</p></main></body></html>';

function privateResponse(response: NextResponse): NextResponse {
  response.headers.set("Cache-Control", "private, no-store");
  response.headers.set("Referrer-Policy", "no-referrer");
  response.headers.append("Vary", "Cookie");
  return response;
}

function denied(request: NextRequest, status?: number): NextResponse {
  const api =
    request.nextUrl.pathname === "/api" || request.nextUrl.pathname.startsWith("/api/");
  return privateResponse(
    api
      ? NextResponse.json(
          {
            detail: {
              code: "access_required",
              message: "専用リンクからアクセスしてください。",
            },
          },
          { status: status || 401 },
        )
      : new NextResponse(restricted, {
          status: status || 403,
          headers: { "Content-Type": "text/html; charset=utf-8" },
        }),
  );
}

export function proxy(request: NextRequest) {
  let secret: string | undefined;
  try {
    secret = accessSecret();
  } catch {
    return denied(request, 503);
  }
  if (!secret) return NextResponse.next();
  const keys = request.nextUrl.searchParams.getAll("key");
  if (keys.length) {
    // Only a page navigation exchanges a shared key; APIs require the cookie.
    if (
      request.method !== "GET" ||
      request.nextUrl.pathname.startsWith("/api") ||
      keys.length !== 1 ||
      !matchesAccessKey(keys[0], secret)
    )
      return denied(request);
    const target = request.nextUrl.clone();
    target.searchParams.delete("key");
    const response = NextResponse.redirect(target, 303);
    response.cookies.set(ACCESS_COOKIE, createAccessToken(secret), {
      httpOnly: true,
      secure:
        process.env.NODE_ENV === "production" ||
        process.env.VERCEL === "1" ||
        request.nextUrl.protocol === "https:",
      sameSite: "lax",
      path: "/",
      maxAge: ACCESS_TTL,
    });
    return privateResponse(response);
  }
  if (!validAccessToken(request.cookies.get(ACCESS_COOKIE)?.value, secret))
    return denied(request);
  return privateResponse(NextResponse.next());
}

export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"] };
