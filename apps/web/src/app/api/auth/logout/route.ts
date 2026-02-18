import { NextResponse } from "next/server";
import { buildHostedLogoutUrl, clearSessionCookies } from "@/lib/server/cognito";

export async function POST() {
  clearSessionCookies();

  let logoutUrl = "/login";
  try {
    logoutUrl = buildHostedLogoutUrl();
  } catch {
    logoutUrl = "/login";
  }

  return NextResponse.json({ logoutUrl });
}
