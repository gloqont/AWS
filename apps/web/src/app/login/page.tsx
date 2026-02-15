"use client";

import { useState } from "react";
import { getCognitoAuthorizeUrl } from "@/lib/auth";

export default function LoginPage() {
  const [error, setError] = useState<string>("");

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
    <main className="relative min-h-screen overflow-hidden bg-[#070b14] text-slate-100">
      <div className="app-bubbles pointer-events-none absolute inset-0 z-0" aria-hidden="true" />
      <div className="relative z-10 mx-auto grid min-h-screen w-full max-w-7xl lg:grid-cols-[1.08fr_1fr]">
        <section className="hidden border-r border-slate-800/80 bg-gradient-to-b from-[#0d1324]/70 via-[#090f1d]/40 to-transparent px-14 py-16 lg:flex lg:items-center">
          <div className="w-full max-w-lg">
            <img src="/gloqont-logo.svg" alt="GLOQONT" className="h-16 w-16 rounded-2xl ring-1 ring-slate-700/70" />
            <p className="mt-7 text-xs uppercase tracking-[0.24em] text-indigo-300">GLOQONT</p>
            <h1 className="mt-4 max-w-md text-5xl font-semibold leading-[1.1] text-white">
              Decision intelligence for recurring investors.
            </h1>
            <p className="mt-6 max-w-md text-base leading-7 text-slate-300">
              Sign in to access your portfolios, scenario simulations, and tax-aware decision history.
            </p>
          </div>
        </section>

        <section className="flex items-center justify-center p-6 sm:p-10">
          <div className="w-full max-w-2xl rounded-3xl border border-slate-800/80 bg-[#0a1020]/75 p-5 shadow-[0_30px_80px_rgba(2,6,23,0.7)] backdrop-blur xl:p-6">
            <div className="mb-5 lg:hidden">
              <img src="/gloqont-logo.svg" alt="GLOQONT" className="h-14 w-14 rounded-2xl ring-1 ring-slate-700/70" />
              <p className="mt-3 text-xs uppercase tracking-[0.2em] text-indigo-300">GLOQONT</p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <article className="rounded-2xl border border-slate-800 bg-slate-950/55 p-5">
                <h2 className="text-center text-lg font-semibold text-white">Login</h2>
                <div className="mt-4 space-y-2">
                  <div className="rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2 text-xs text-slate-500">email</div>
                  <div className="rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2 text-xs text-slate-500">password</div>
                </div>
                <button
                  type="button"
                  onClick={() => startLogin("login")}
                  className="mt-4 w-full rounded-lg bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-400"
                >
                  Login
                </button>
                <div className="my-4 h-px bg-slate-800" />
                <div className="space-y-2">
                  <button
                    type="button"
                    onClick={() => startLogin("login", "Facebook")}
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-slate-100 hover:bg-slate-800"
                  >
                    Login with Facebook
                  </button>
                  <button
                    type="button"
                    onClick={() => startLogin("login", "Google")}
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-slate-100 hover:bg-slate-800"
                  >
                    Login with Google
                  </button>
                </div>
              </article>

              <article className="rounded-2xl border border-slate-800 bg-slate-950/55 p-5">
                <h2 className="text-center text-lg font-semibold text-white">Signup</h2>
                <div className="mt-4 space-y-2">
                  <div className="rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2 text-xs text-slate-500">email</div>
                  <div className="rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2 text-xs text-slate-500">create password</div>
                  <div className="rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2 text-xs text-slate-500">confirm password</div>
                </div>
                <button
                  type="button"
                  onClick={() => startLogin("signup")}
                  className="mt-4 w-full rounded-lg bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-400"
                >
                  Signup
                </button>
                <div className="my-4 h-px bg-slate-800" />
                <div className="space-y-2">
                  <button
                    type="button"
                    onClick={() => startLogin("signup", "Facebook")}
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-slate-100 hover:bg-slate-800"
                  >
                    Signup with Facebook
                  </button>
                  <button
                    type="button"
                    onClick={() => startLogin("signup", "Google")}
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-slate-100 hover:bg-slate-800"
                  >
                    Signup with Google
                  </button>
                  <button
                    type="button"
                    onClick={() => startLogin("signup", "SignInWithApple")}
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-slate-100 hover:bg-slate-800"
                  >
                    Signup with Apple
                  </button>
                </div>
              </article>
            </div>

            {error ? (
              <p className="mt-4 rounded-lg border border-red-500/30 bg-red-950/30 px-3 py-2 text-sm text-red-200">
                {error}
              </p>
            ) : null}
          </div>
        </section>
      </div>
    </main>
  );
}
