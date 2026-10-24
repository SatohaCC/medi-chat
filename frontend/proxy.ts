import { type NextRequest, NextResponse } from "next/server";

/** Display-layer response policy. FastAPI owns authentication and authorization. */
export function proxy(_request: NextRequest) {
  const response = NextResponse.next();
  response.headers.set("Cache-Control", "private, no-store");
  response.headers.set("Referrer-Policy", "no-referrer");
  response.headers.append("Vary", "Cookie");
  return response;
}

export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"] };
