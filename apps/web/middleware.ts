import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(req: NextRequest) {
  // Bypass authentication middleware so frontend routes render without login.
  // This intentionally allows access to dashboard pages in local/dev environments.
  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/login"],
};
