import { NextResponse } from "next/server";
import { claimAsString, getIdTokenFromCookies, verifyIdToken } from "@/lib/server/cognito";

export async function GET() {
  try {
    const token = getIdTokenFromCookies();
    if (!token) {
      return NextResponse.json({ authenticated: false }, { status: 401 });
    }

    const claims = await verifyIdToken(token);
    return NextResponse.json({
      authenticated: true,
      user: {
        sub: claims.sub,
        email: claimAsString(claims.email) || null,
        name: claimAsString(claims.name) || claimAsString(claims["cognito:username"]) || null,
      },
    });
  } catch (error: any) {
    return NextResponse.json({ authenticated: false, error: error?.message || "Invalid session" }, { status: 401 });
  }
}
