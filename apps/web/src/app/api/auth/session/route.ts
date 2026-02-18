import { NextResponse } from "next/server";
import { claimAsString, clearSessionCookies, setSessionCookies, verifyIdToken } from "@/lib/server/cognito";
import { upsertUserProfileFromClaims } from "@/lib/server/user-sync";

export async function POST(req: Request) {
  try {
    const body = (await req.json()) as {
      idToken?: string;
      accessToken?: string;
      refreshToken?: string;
      rememberMe?: boolean;
    };

    const idToken = body.idToken?.trim() || "";
    const accessToken = body.accessToken?.trim() || "";

    if (!idToken || !accessToken) {
      return NextResponse.json({ error: "Missing idToken or accessToken" }, { status: 400 });
    }

    const claims = await verifyIdToken(idToken);

    setSessionCookies({
      idToken,
      accessToken,
      refreshToken: body.refreshToken?.trim() || undefined,
      rememberMe: Boolean(body.rememberMe),
    });

    try {
      await upsertUserProfileFromClaims({
        sub: claims.sub,
        email: claimAsString(claims.email),
        name: claimAsString(claims.name),
        "cognito:username": claimAsString(claims["cognito:username"]),
      });
    } catch (syncError) {
      console.error("user sync failed after session set", syncError);
    }

    return NextResponse.json({ ok: true, sub: claims.sub, email: claimAsString(claims.email) || null });
  } catch (error: any) {
    clearSessionCookies();
    return NextResponse.json({ error: error?.message || "Invalid token" }, { status: 401 });
  }
}
