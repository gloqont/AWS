import { NextResponse } from "next/server";
import { getIdTokenFromCookies, verifyIdToken } from "@/lib/server/cognito";
import { upsertUserProfileFromClaims } from "@/lib/server/user-sync";

export async function POST() {
  try {
    const token = getIdTokenFromCookies();
    if (!token) {
      return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    }

    const claims = await verifyIdToken(token);
    const profile = await upsertUserProfileFromClaims({
      sub: claims.sub,
      email: claims.email,
      name: claims.name,
      "cognito:username": claims["cognito:username"] as string | undefined,
    });

    return NextResponse.json({ ok: true, profile });
  } catch (error: any) {
    return NextResponse.json({ error: error?.message || "Could not sync user" }, { status: 500 });
  }
}
