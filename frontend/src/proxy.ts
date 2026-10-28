import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { AUTH_COOKIES } from "./lib/auth";

export default function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const accessToken = request.cookies.get(AUTH_COOKIES.ACCESS_TOKEN)?.value;
  const refreshToken = request.cookies.get(AUTH_COOKIES.REFRESH_TOKEN)?.value;
  const userSession = request.cookies.get(AUTH_COOKIES.USER_SESSION)?.value;
  const hasSessionEvidence = Boolean(accessToken || refreshToken);

  // Auth page redirect (already logged in → app)
  if (pathname === "/login" && accessToken && userSession) {
    return NextResponse.redirect(new URL("/liquidaciones", request.url));
  }

  // Redirect to login if no token and trying to access protected area
  if (!hasSessionEvidence && !pathname.startsWith("/login")) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|images|favicon.ico).*)"],
};
