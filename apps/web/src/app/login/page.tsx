"use client";

import { useMemo, useState } from "react";
import { getCognitoAuthorizeUrl } from "@/lib/auth";

export default function LoginPage() {
  const [error, setError] = useState<string>("");
  const year = useMemo(() => new Date().getFullYear(), []);

  function startLogin(mode: "login" | "signup", provider?: "Google" | "Facebook" | "SignInWithApple") {
    try {
      const url = getCognitoAuthorizeUrl({
        mode,
        provider,
        state: "/dashboard/portfolio-optimizer",
      });
      window.location.href = url;
    } catch (e: any) {
      setError(e?.message || "Unable to start sign-in.");
    }
  }

  return (
    <main className="min-h-screen bg-[#0a0d14] text-slate-100">
      <div className="mx-auto grid min-h-screen w-full max-w-6xl lg:grid-cols-2">
        <section className="hidden border-r border-slate-800/80 bg-gradient-to-b from-[#0e1423] via-[#0a0d14] to-[#0a0d14] p-12 lg:flex lg:flex-col lg:justify-between">
          <div>
            <img src="/gloqont-logo.svg" alt="GLOQONT" className="h-16 w-16 rounded-2xl" />
            <p className="mt-8 text-sm uppercase tracking-[0.2em] text-indigo-300">GLOQONT</p>
            <h1 className="mt-3 max-w-md text-4xl font-semibold leading-tight text-white">
              Decision intelligence for recurring investors.
            </h1>
            <p className="mt-5 max-w-md text-sm leading-6 text-slate-300">
              Sign in to access your portfolios, scenario simulations, and tax-aware decision history.
            </p>
          </div>
          <p className="text-xs text-slate-500">© {year} GLOQONT</p>
        </section>

        <section className="flex items-center justify-center p-6 sm:p-10">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/70 p-7 shadow-[0_20px_60px_rgba(0,0,0,0.45)] backdrop-blur">
            <div className="mb-6 lg:hidden">
              <img src="/gloqont-logo.svg" alt="GLOQONT" className="h-14 w-14 rounded-2xl" />
              <p className="mt-3 text-xs uppercase tracking-[0.16em] text-indigo-300">GLOQONT</p>
            </div>

            <h2 className="text-2xl font-semibold text-white">Welcome back</h2>
            <p className="mt-2 text-sm text-slate-300">Secure sign-in with Cognito and social providers.</p>

            <div className="mt-6 grid gap-3">
              <button
                type="button"
                onClick={() => startLogin("login")}
                className="rounded-xl bg-indigo-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-400"
              >
                Continue With Email
              </button>
              <button
                type="button"
                onClick={() => startLogin("signup")}
                className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm font-semibold text-slate-100 transition hover:bg-slate-800"
              >
                Create Account
              </button>
            </div>

            <div className="my-6 h-px bg-slate-800" />

            <div className="grid gap-3">
              <button
                type="button"
                onClick={() => startLogin("login", "Google")}
                className="rounded-xl border border-slate-700 bg-[#111827] px-4 py-3 text-sm font-medium text-slate-100 hover:bg-[#1f2937]"
              >
                Continue With Google
              </button>
              <button
                type="button"
                onClick={() => startLogin("login", "Facebook")}
                className="rounded-xl border border-slate-700 bg-[#111827] px-4 py-3 text-sm font-medium text-slate-100 hover:bg-[#1f2937]"
              >
                Continue With Facebook
              </button>
              <button
                type="button"
                onClick={() => startLogin("login", "SignInWithApple")}
                className="rounded-xl border border-slate-700 bg-[#111827] px-4 py-3 text-sm font-medium text-slate-100 hover:bg-[#1f2937]"
              >
                Continue With Apple
              </button>
            </div>

            {error ? (
              <p className="mt-5 rounded-lg border border-red-500/30 bg-red-950/30 px-3 py-2 text-sm text-red-200">
                {error}
              </p>
            ) : null}
          </div>
        </section>
      </div>
    </main>
  );
}
