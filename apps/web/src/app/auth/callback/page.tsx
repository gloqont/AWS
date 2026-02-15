"use client";

import { useEffect, useState } from "react";
import { clearAuthToken, saveAuthToken } from "@/lib/auth";

function parseHash(hash: string) {
  const normalized = hash.startsWith("#") ? hash.slice(1) : hash;
  return new URLSearchParams(normalized);
}

export default function AuthCallbackPage() {
  const [message, setMessage] = useState("Finalizing sign-in...");

  useEffect(() => {
    try {
      clearAuthToken();
      const params = parseHash(window.location.hash || "");
      const accessToken = params.get("access_token");
      const idToken = params.get("id_token");
      const error = params.get("error");
      const errorDescription = params.get("error_description");
      const state = params.get("state");

      if (error) {
        const msg = errorDescription || error;
        setMessage(`Sign-in failed: ${msg}`);
        setTimeout(() => {
          window.location.href = "/login";
        }, 1800);
        return;
      }

      const token = idToken || accessToken;
      if (!token) {
        setMessage("Missing auth token from Cognito response.");
        setTimeout(() => {
          window.location.href = "/login";
        }, 1800);
        return;
      }

      saveAuthToken(token);
      const nextPath = state && state.startsWith("/") ? state : "/dashboard/portfolio-optimizer";
      window.location.href = nextPath;
    } catch {
      setMessage("Sign-in callback could not be processed.");
      setTimeout(() => {
        window.location.href = "/login";
      }, 1800);
    }
  }, []);

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#0a0d14] text-slate-100">
      <div className="rounded-xl border border-slate-800 bg-slate-900/80 px-6 py-5 text-sm text-slate-200">
        {message}
      </div>
    </main>
  );
}
