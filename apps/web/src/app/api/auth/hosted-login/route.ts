import { NextResponse } from "next/server";
import {
  buildHostedAuthorizeUrl,
  generatePkceVerifier,
  generateState,
  pkceChallengeFromVerifier,
  setOAuthStartCookies,
} from "@/lib/server/cognito";

type Provider = "Google" | "Facebook" | "SignInWithApple";

function parseProvider(value: unknown): Provider | undefined {
  if (value === "Google" || value === "Facebook" || value === "SignInWithApple") {
    return value;
  }
  return undefined;
}

function parseMode(value: unknown): "signin" | "signup" {
  return value === "signup" ? "signup" : "signin";
}

export async function POST(req: Request) {
  try {
    const body = (await req.json().catch(() => ({}))) as {
      mode?: "signin" | "signup";
      provider?: Provider;
      nextPath?: string;
      rememberMe?: boolean;
    };

    const mode = parseMode(body.mode);
    const provider = parseProvider(body.provider);
    const state = generateState();
    const codeVerifier = generatePkceVerifier();
    const codeChallenge = pkceChallengeFromVerifier(codeVerifier);

    setOAuthStartCookies({
      state,
      codeVerifier,
      nextPath: body.nextPath,
      rememberMe: body.rememberMe,
    });

    const url = buildHostedAuthorizeUrl({
      state,
      mode,
      provider,
      codeChallenge,
    });

    return NextResponse.json({ url });
  } catch (error: any) {
    return NextResponse.json(
      {
        error: error?.message || "Could not start social sign in",
      },
      { status: 400 },
    );
  }
}
