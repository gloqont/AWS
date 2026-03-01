import { createHash, randomBytes } from "crypto";
import { cookies } from "next/headers";
import { CognitoJwtVerifier } from "aws-jwt-verify";

const COOKIE_ID_TOKEN = "gloqont_id_token";
const COOKIE_ACCESS_TOKEN = "gloqont_access_token";
const COOKIE_REFRESH_TOKEN = "gloqont_refresh_token";
const COOKIE_AUTH_TOKEN = "gloqont_auth_token";
const COOKIE_STATE = "gloqont_oauth_state";
const COOKIE_PKCE_VERIFIER = "gloqont_oauth_pkce_verifier";
const COOKIE_POST_AUTH_REDIRECT = "gloqont_post_auth_redirect";
const COOKIE_REMEMBER_ME = "gloqont_remember_me";

const OAUTH_SCOPE = "openid email profile";
const DEFAULT_AFTER_LOGIN = "/dashboard/portfolio-optimizer";

function requiredEnv(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) {
    throw new Error(`Missing required env var: ${name}`);
  }
  return value;
}

function optionalEnv(name: string): string {
  return process.env[name]?.trim() || "";
}

function normalizeDomain(value: string): string {
  if (value.startsWith("http://") || value.startsWith("https://")) {
    return value.replace(/\/$/, "");
  }
  return `https://${value.replace(/\/$/, "")}`;
}

export function cognitoConfig() {
  const region = requiredEnv("COGNITO_REGION");
  const userPoolId = requiredEnv("COGNITO_USER_POOL_ID");
  const clientId = requiredEnv("COGNITO_CLIENT_ID");
  const domain = normalizeDomain(requiredEnv("COGNITO_DOMAIN"));
  const redirectUri = requiredEnv("COGNITO_REDIRECT_URI");
  const logoutUri = requiredEnv("COGNITO_LOGOUT_URI");
  const clientSecret = optionalEnv("COGNITO_CLIENT_SECRET");

  return {
    region,
    userPoolId,
    clientId,
    clientSecret,
    domain,
    redirectUri,
    logoutUri,
  };
}

const verifierByPool = new Map<string, ReturnType<typeof CognitoJwtVerifier.create>>();

export async function verifyIdToken(token: string) {
  const { userPoolId, clientId } = cognitoConfig();
  const cacheKey = `${userPoolId}:${clientId}`;

  if (!verifierByPool.has(cacheKey)) {
    verifierByPool.set(
      cacheKey,
      CognitoJwtVerifier.create({
        userPoolId,
        tokenUse: "id",
        clientId,
      }),
    );
  }

  const verifier = verifierByPool.get(cacheKey)!;
  return verifier.verify(token);
}

export function claimAsString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined;
}

function base64Url(input: Buffer) {
  return input.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export function generateState(): string {
  return base64Url(randomBytes(24));
}

export function generatePkceVerifier(): string {
  return base64Url(randomBytes(64));
}

export function pkceChallengeFromVerifier(verifier: string): string {
  return base64Url(createHash("sha256").update(verifier).digest());
}

function cookieBaseOptions(maxAge?: number) {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    ...(typeof maxAge === "number" ? { maxAge } : {}),
  };
}

export function clearSessionCookies() {
  const store = cookies();
  store.delete(COOKIE_ID_TOKEN);
  store.delete(COOKIE_ACCESS_TOKEN);
  store.delete(COOKIE_REFRESH_TOKEN);
  store.delete(COOKIE_AUTH_TOKEN);
  clearOAuthCookies();
}

export function clearOAuthCookies() {
  const store = cookies();
  store.delete(COOKIE_STATE);
  store.delete(COOKIE_PKCE_VERIFIER);
  store.delete(COOKIE_POST_AUTH_REDIRECT);
  store.delete(COOKIE_REMEMBER_ME);
}

export function setOAuthStartCookies(params: {
  state: string;
  codeVerifier: string;
  nextPath?: string;
  rememberMe?: boolean;
}) {
  const store = cookies();
  store.set(COOKIE_STATE, params.state, cookieBaseOptions(10 * 60));
  store.set(COOKIE_PKCE_VERIFIER, params.codeVerifier, cookieBaseOptions(10 * 60));
  store.set(
    COOKIE_POST_AUTH_REDIRECT,
    params.nextPath && params.nextPath.startsWith("/") ? params.nextPath : DEFAULT_AFTER_LOGIN,
    cookieBaseOptions(10 * 60),
  );
  store.set(COOKIE_REMEMBER_ME, params.rememberMe ? "1" : "0", cookieBaseOptions(10 * 60));
}

export function readOAuthCookies() {
  const store = cookies();
  return {
    state: store.get(COOKIE_STATE)?.value || "",
    codeVerifier: store.get(COOKIE_PKCE_VERIFIER)?.value || "",
    nextPath: store.get(COOKIE_POST_AUTH_REDIRECT)?.value || DEFAULT_AFTER_LOGIN,
    rememberMe: store.get(COOKIE_REMEMBER_ME)?.value === "1",
  };
}

export function setSessionCookies(tokens: {
  idToken: string;
  accessToken: string;
  refreshToken?: string;
  rememberMe?: boolean;
}) {
  const store = cookies();
  const maxAge = tokens.rememberMe ? 60 * 60 * 24 * 30 : undefined;

  store.set(COOKIE_ID_TOKEN, tokens.idToken, cookieBaseOptions(maxAge));
  store.set(COOKIE_ACCESS_TOKEN, tokens.accessToken, cookieBaseOptions(maxAge));
  store.set(COOKIE_AUTH_TOKEN, tokens.idToken, cookieBaseOptions(maxAge));

  if (tokens.refreshToken) {
    store.set(COOKIE_REFRESH_TOKEN, tokens.refreshToken, cookieBaseOptions(60 * 60 * 24 * 30));
  }
}

export function getIdTokenFromCookies(): string {
  const store = cookies();
  return store.get(COOKIE_ID_TOKEN)?.value || store.get(COOKIE_AUTH_TOKEN)?.value || "";
}

export function getAccessTokenFromCookies(): string {
  return cookies().get(COOKIE_ACCESS_TOKEN)?.value || "";
}

export async function exchangeAuthorizationCode(params: { code: string; codeVerifier: string }) {
  const config = cognitoConfig();
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code: params.code,
    client_id: config.clientId,
    redirect_uri: config.redirectUri,
    code_verifier: params.codeVerifier,
  });

  const headers = new Headers({
    "Content-Type": "application/x-www-form-urlencoded",
  });

  if (config.clientSecret) {
    const basic = Buffer.from(`${config.clientId}:${config.clientSecret}`).toString("base64");
    headers.set("Authorization", `Basic ${basic}`);
  }

  const res = await fetch(`${config.domain}/oauth2/token`, {
    method: "POST",
    headers,
    body: body.toString(),
    cache: "no-store",
  });

  const text = await res.text();
  if (!res.ok) {
    throw new Error(`Token exchange failed (${res.status}): ${text}`);
  }

  const payload = JSON.parse(text) as {
    id_token?: string;
    access_token?: string;
    refresh_token?: string;
  };

  if (!payload.id_token || !payload.access_token) {
    throw new Error("Cognito token response is missing id_token or access_token");
  }

  return {
    idToken: payload.id_token,
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token,
  };
}

export function buildHostedAuthorizeUrl(params: {
  state: string;
  mode: "signin" | "signup";
  provider?: "Google" | "Facebook" | "SignInWithApple";
  codeChallenge: string;
}) {
  const config = cognitoConfig();
  const url = new URL(`${config.domain}/oauth2/authorize`);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("client_id", config.clientId);
  url.searchParams.set("redirect_uri", config.redirectUri);
  url.searchParams.set("scope", OAUTH_SCOPE);
  url.searchParams.set("state", params.state);
  url.searchParams.set("code_challenge_method", "S256");
  url.searchParams.set("code_challenge", params.codeChallenge);

  if (params.mode === "signup") {
    url.searchParams.set("screen_hint", "signup");
  }

  if (params.provider) {
    url.searchParams.set("identity_provider", params.provider);
  }

  return url.toString();
}

export function buildHostedLogoutUrl() {
  const config = cognitoConfig();
  const url = new URL(`${config.domain}/logout`);
  url.searchParams.set("client_id", config.clientId);
  url.searchParams.set("logout_uri", config.logoutUri);
  return url.toString();
}

export const authCookieNames = {
  idToken: COOKIE_ID_TOKEN,
  accessToken: COOKIE_ACCESS_TOKEN,
  refreshToken: COOKIE_REFRESH_TOKEN,
  authToken: COOKIE_AUTH_TOKEN,
};
