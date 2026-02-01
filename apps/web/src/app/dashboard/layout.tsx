"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { ThemeToggle } from "@/components/theme-toggle";

const nav = [
  { label: "Portfolio Optimizer", href: "/dashboard/portfolio-optimizer", id: "portfolio-optimizer-link" },
  { label: "Scenario Simulation", href: "/dashboard/scenario-simulation", id: "scenario-simulation-link" },
  { label: "Tax Advisor", href: "/dashboard/tax-advisor", id: "tax-advisor-link" },
  { label: "Tax Impact", href: "/dashboard/tax-impact", id: "tax-impact-link" }, // ✅ added
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  // Persist collapsed state
  useEffect(() => {
    const saved = localStorage.getItem("sidebar_collapsed");
    if (saved) setCollapsed(saved === "1");
  }, []);
  useEffect(() => {
    localStorage.setItem("sidebar_collapsed", collapsed ? "1" : "0");
  }, [collapsed]);

  async function logout() {
    try {
      await apiFetch("/api/v1/auth/logout", { method: "POST" });
    } finally {
      window.location.href = "/login";
    }
  }

  function restartPortfolioTutorial() {
    localStorage.removeItem("hasCompletedTutorial");
    localStorage.setItem("forcePortfolioTutorial", "1");
    window.location.href = "/dashboard/portfolio-optimizer";
  }

  return (
    <div className="min-h-screen flex bg-background text-foreground">
      {/* Sidebar */}
      <aside
        className={[
          "sticky top-0 h-screen shrink-0 border-r border-border bg-card/80 backdrop-blur",
          "transition-all duration-200 ease-out",
          collapsed ? "w-20" : "w-72",
        ].join(" ")}
      >
        <div className="h-full flex flex-col">
          {/* Brand */}
          <div className="px-4 py-4 border-b border-border">
            <div className={collapsed ? "flex flex-col items-center gap-3" : "flex items-center justify-between gap-3"}>
              <div className="flex items-center gap-3 min-w-0">
                <img
                  src="/gloqont-logo.svg"
                  alt="GLOQONT"
                  className="h-14 w-14 shrink-0 rounded-2xl"
                />
                <div className={collapsed ? "hidden" : "min-w-0"}>
                  <div className="text-xs text-muted-foreground">GLOQONT</div>
                  <div className="text-sm font-semibold tracking-tight">Admin Console</div>
                </div>
              </div>

              <button
                onClick={() => setCollapsed((v) => !v)}
                className={collapsed
                  ? "rounded-xl border border-border bg-card px-2 py-2 text-xs hover:bg-muted"
                  : "rounded-xl border border-border bg-card px-3 py-2 text-xs hover:bg-muted"}
                aria-label="Toggle sidebar"
                title="Toggle sidebar"
              >
                {collapsed ? "→" : "←"}
              </button>
            </div>
          </div>

          {/* Nav */}
          <nav className="px-3 py-3 flex-1">
            {!collapsed && (
              <div className="px-2 py-2 text-xs text-muted-foreground">
                NAVIGATION
              </div>
            )}

            <div className="space-y-1">
              {nav.map((item) => {
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    id={item.id}
                    href={item.href}
                    className={[
                      "flex items-center rounded-xl border transition-colors",
                      collapsed ? "justify-center px-2 py-2" : "gap-3 px-3 py-2",
                      active
                        ? "bg-primary text-primary-foreground border-primary"
                        : "bg-transparent text-foreground border-transparent hover:bg-muted hover:border-border",
                    ].join(" ")}
                  >
                    <span className={["h-2.5 w-2.5 rounded-full", active ? "bg-primary-foreground" : "bg-muted-foreground/60"].join(" ")} />
                    <span className={collapsed ? "hidden" : "text-sm"}>{item.label}</span>
                  </Link>
                );
              })}

            </div>
          </nav>

          {/* Logout at bottom */}
          <div className="px-3 pb-4">
            <button
              onClick={restartPortfolioTutorial}
              className="mb-2 w-full rounded-xl border border-border bg-card px-3 py-2 text-sm hover:bg-muted"
            >
              {collapsed ? "▶" : "Restart Tutorial"}
            </button>
            <button
              onClick={logout}
              className="w-full rounded-xl border border-border bg-card px-3 py-2 text-sm hover:bg-muted"
            >
              {collapsed ? "⎋" : "Logout"}
            </button>
          </div>

          <div className="px-4 py-4 border-t border-border text-xs text-muted-foreground">
            {collapsed ? (
              <div className="flex justify-center">
                <ThemeToggle compact />
              </div>
            ) : (
              <div className="flex items-start justify-between gap-3">
                <div className="leading-relaxed">
                  v1 • admin-only
                  <br />
                  Protected routes
                </div>
                <ThemeToggle />
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="relative flex-1 min-w-0 min-h-screen overflow-hidden">
        <div className="app-bubbles pointer-events-none absolute inset-0 z-0" aria-hidden="true" />
        <div className="relative z-10">
          {children}
        </div>
      </main>
    </div>
  );
}
