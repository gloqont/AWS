import { NextResponse } from "next/server";
import {
  clearOAuthCookies,
  clearSessionCookies,
  exchangeAuthorizationCode,
  readOAuthCookies,
  setSessionCookies,
  verifyIdToken,
} from "@/lib/server/cognito";
import { upsertUserProfileFromClaims } from "@/lib/server/user-sync";

const LOGIN_PATH = "/login";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const code = url.searchParams.get("code") || "";
  const state = url.searchParams.get("state") || "";
  const error = url.searchParams.get("error") || "";
  const errorDescription = url.searchParams.get("error_description") || "";

  if (error) {
    const to = new URL(LOGIN_PATH, url.origin);
    to.searchParams.set("error", errorDescription || error);
    return NextResponse.redirect(to);
  }

  if (!code || !state) {
    const to = new URL(LOGIN_PATH, url.origin);
    to.searchParams.set("error", "Missing code or state in callback");
    return NextResponse.redirect(to);
  }

  try {
    const oauth = readOAuthCookies();
    if (!oauth.state || oauth.state !== state) {
      throw new Error("OAuth state mismatch");
    }

    const tokens = await exchangeAuthorizationCode({
      code,
      codeVerifier: oauth.codeVerifier,
    });

    const claims = await verifyIdToken(tokens.idToken);

    setSessionCookies({
      idToken: tokens.idToken,
      accessToken: tokens.accessToken,
      refreshToken: tokens.refreshToken,
      rememberMe: oauth.rememberMe,
    });
    clearOAuthCookies();

    try {
      await upsertUserProfileFromClaims({
        sub: claims.sub,
        email: claims.email,
        name: claims.name,
        "cognito:username": claims["cognito:username"] as string | undefined,
      });
    } catch (syncError) {
      console.error("user sync failed after callback", syncError);
    }

    const safePath = oauth.nextPath && oauth.nextPath.startsWith("/") ? oauth.nextPath : "/dashboard/portfolio-optimizer";
    return NextResponse.redirect(new URL(safePath, url.origin));
  } catch (callbackError: any) {
    clearSessionCookies();
    const to = new URL(LOGIN_PATH, url.origin);
    to.searchParams.set("error", callbackError?.message || "Authentication callback failed");
    return NextResponse.redirect(to);
  }
}
