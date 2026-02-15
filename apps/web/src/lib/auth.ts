const TOKEN_KEY = "gloqont_auth_token";
const COOKIE_KEY = "gloqont_auth_token";
const DEFAULT_SCOPES = "openid email profile";

function baseOrigin() {
  if (typeof window === "undefined") return "";
  return window.location.origin;
}

function getEnv(name: string): string {
  const v = process.env[name];
  return typeof v === "string" ? v.trim() : "";
}

function cookieFromDocument(name: string): string | null {
  if (typeof document === "undefined") return null;
  const parts = document.cookie.split(";").map((c) => c.trim());
  for (const part of parts) {
    if (part.startsWith(`${name}=`)) {
      return decodeURIComponent(part.slice(name.length + 1));
    }
  }
  return null;
}

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  const fromStorage = localStorage.getItem(TOKEN_KEY);
  if (fromStorage) return fromStorage;
  return cookieFromDocument(COOKIE_KEY);
}

export function saveAuthToken(token: string) {
  if (typeof window === "undefined") return;
  const safeToken = token.trim();
  if (!safeToken) return;
  localStorage.setItem(TOKEN_KEY, safeToken);
  const secure = window.location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${COOKIE_KEY}=${encodeURIComponent(safeToken)}; Path=/; Max-Age=2592000; SameSite=Lax${secure}`;
}

export function clearAuthToken() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  const secure = window.location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${COOKIE_KEY}=; Path=/; Max-Age=0; SameSite=Lax${secure}`;
}

export function authConfig() {
  const domain = getEnv("NEXT_PUBLIC_COGNITO_DOMAIN");
  const clientId = getEnv("NEXT_PUBLIC_COGNITO_CLIENT_ID");
  const redirectUri = getEnv("NEXT_PUBLIC_COGNITO_REDIRECT_URI") || `${baseOrigin()}/auth/callback`;
  const logoutUri = getEnv("NEXT_PUBLIC_COGNITO_LOGOUT_REDIRECT_URI") || `${baseOrigin()}/login`;
  return { domain, clientId, redirectUri, logoutUri };
}

export function getCognitoAuthorizeUrl(opts: {
  mode?: "login" | "signup";
  provider?: "Google" | "Facebook" | "SignInWithApple";
  state?: string;
} = {}): string {
  const { domain, clientId, redirectUri } = authConfig();
  if (!domain || !clientId || !redirectUri) {
    throw new Error("Missing Cognito config. Set NEXT_PUBLIC_COGNITO_DOMAIN and NEXT_PUBLIC_COGNITO_CLIENT_ID.");
  }
  const url = new URL(`${domain.replace(/\/$/, "")}/login`);
  url.searchParams.set("client_id", clientId);
  url.searchParams.set("response_type", "token");
  url.searchParams.set("scope", DEFAULT_SCOPES);
  url.searchParams.set("redirect_uri", redirectUri);
  url.searchParams.set("state", opts.state || "/dashboard/portfolio-optimizer");
  if (opts.mode === "signup") {
    url.searchParams.set("screen_hint", "signup");
  }
  if (opts.provider) {
    url.searchParams.set("identity_provider", opts.provider);
  }
  return url.toString();
}

export function getCognitoLogoutUrl(): string {
  const { domain, clientId, logoutUri } = authConfig();
  if (!domain || !clientId || !logoutUri) return "/login";
  const url = new URL(`${domain.replace(/\/$/, "")}/logout`);
  url.searchParams.set("client_id", clientId);
  url.searchParams.set("logout_uri", logoutUri);
  return url.toString();
}
