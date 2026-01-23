"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { apiFetch } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "/dashboard/portfolio-optimizer";

  const [email, setEmail] = useState("admin@admin.com");
  const [password, setPassword] = useState("admin123");
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setLoading(true);
    try {
      await apiFetch("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ username: email, password }), // API still expects 'username' field
      });
      // Reset tutorial completion flag on login to show tutorial on dashboard visit
      localStorage.removeItem('hasCompletedTutorial');
      // Navigate directly to dashboard after login
      router.push(next);
    } catch (e: any) {
      setErr(e.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-6 shadow-xl">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold tracking-tight mb-2">GLOQONT</h1>
          <p className="text-sm text-white/80 mb-4">See What Happens to Your Portfolio BEFORE You Make the Decision</p>

          <div className="mb-6 space-y-4">
            <div className="text-xs text-white/60">Why GLOQONT?</div>
            <ul className="text-xs text-white/70 space-y-1">
              <li>• Portfolio-wide impact analysis - Not just single stock moves</li>
              <li>• Real-time consequence modeling - Before you commit capital</li>
              <li>• Cross-asset correlation detection - See hidden risks</li>
              <li>• Irreversibility warnings - Know what can't be undone</li>
            </ul>
          </div>

          <div className="text-sm text-white/60 mb-4">Start Your Free Analysis</div>
        </div>

        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="text-sm text-white/70">Email Address</label>
            <input
              className="mt-1 w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 outline-none focus:border-white/25"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              autoComplete="email"
            />
          </div>

          <div>
            <label className="text-sm text-white/70">Password</label>
            <input
              className="mt-1 w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 outline-none focus:border-white/25"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              autoComplete="current-password"
            />
          </div>

          {err && (
            <div className="text-sm rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-red-200">
              {err}
            </div>
          )}

          <button
            disabled={loading}
            className="w-full rounded-xl bg-white text-black font-medium py-2.5 hover:opacity-90 disabled:opacity-60"
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <div className="mt-4 text-xs text-white/50 text-center">
          Tip: set credentials in <code className="text-white/70">apps/api/.env</code>
        </div>
      </div>
    </div>
  );
}
