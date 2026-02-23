"use client";

import Link from "next/link";

export default function SignupPage() {
  const signUpHref = "/api/v1/auth/login?mode=signup&next=%2Fdashboard%2Fportfolio-optimizer";

  return (
    <main className="min-h-screen bg-[#050505] text-white flex items-center justify-center px-6">
      <div className="w-full max-w-lg rounded-2xl border border-[#D4A853]/20 bg-black/60 backdrop-blur-xl p-8">
        <h1 className="text-2xl font-semibold tracking-tight">Create Account</h1>
        <p className="mt-3 text-white/70 text-sm leading-relaxed">
          Account creation is secured through Cognito. Continue below to create your account.
        </p>

        <div className="mt-6 flex gap-3">
          <a
            href={signUpHref}
            className="inline-flex items-center rounded-lg bg-[#D4A853] px-4 py-2 text-sm font-semibold text-black hover:bg-[#c89c45]"
          >
            Continue to Sign Up
          </a>
          <Link
            href="/login"
            className="inline-flex items-center rounded-lg border border-white/15 bg-white/5 px-4 py-2 text-sm hover:bg-white/10"
          >
            Back to Sign In
          </Link>
        </div>
      </div>
    </main>
  );
}
