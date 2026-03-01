import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const DASHBOARD_HOME = "/dashboard/portfolio-optimizer";
const AUTH_BYPASS = process.env.NEXT_PUBLIC_AUTH_BYPASS?.trim().toLowerCase() === "true";

export function middleware(req: NextRequest) {
  if (AUTH_BYPASS) {
    if (req.nextUrl.pathname === "/" || req.nextUrl.pathname === "/login") {
      return NextResponse.redirect(new URL(DASHBOARD_HOME, req.url));
    }
    return NextResponse.next();
  }

  const token = req.cookies.get("gloqont_id_token")?.value || req.cookies.get("gloqont_auth_token")?.value;
  const isAuthed = Boolean(token);
  const { pathname } = req.nextUrl;

  if (pathname.startsWith("/dashboard") && !isAuthed) {
    return NextResponse.redirect(new URL("/login", req.url));
  }

  if ((pathname === "/login" || pathname === "/") && isAuthed) {
    return NextResponse.redirect(new URL(DASHBOARD_HOME, req.url));
  }

  if (pathname === "/" && !isAuthed) {
    return NextResponse.redirect(new URL("/login", req.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/", "/login", "/dashboard/:path*"],
};
