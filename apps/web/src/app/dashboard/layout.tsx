"use client";

import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { useTutorial } from "@/components/tutorial/TutorialContext";
import {
  FIRST_TIME_TUTORIAL_STEPS,
  PORTFOLIO_OPTIMIZER_TUTORIAL,
  TAX_ADVISOR_TUTORIAL,
  SCENARIO_SIMULATION_TUTORIAL,
  TAX_IMPACT_TUTORIAL
} from "@/components/tutorial/tutorialContent";

const nav = [
  { label: "Portfolio Optimizer", href: "/dashboard/portfolio-optimizer", id: "portfolio-optimizer-link" },
  { label: "Scenario Simulation", href: "/dashboard/scenario-simulation", id: "scenario-simulation-link" },
  { label: "Tax Advisor", href: "/dashboard/tax-advisor", id: "tax-advisor-link" },
  { label: "Tax Impact", href: "/dashboard/tax-impact", id: "tax-impact-link" }, // ✅ added
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const { isTutorialActive, startTutorial } = useTutorial();

  // Persist collapsed state
  useEffect(() => {
    const saved = localStorage.getItem("sidebar_collapsed");
    if (saved) setCollapsed(saved === "1");
  }, []);
  useEffect(() => {
    localStorage.setItem("sidebar_collapsed", collapsed ? "1" : "0");
  }, [collapsed]);

  // Check if user is new and start the first-time tutorial
  useEffect(() => {
    const hasCompletedTutorial = localStorage.getItem('hasCompletedTutorial');

    // Show the tutorial for users who haven't completed it yet
    if (!hasCompletedTutorial) {
      // Small delay to ensure DOM is ready
      const timer = setTimeout(() => {
        // Navigate to the portfolio optimizer page with tutorial parameter
        router.push('/dashboard/portfolio-optimizer?tutorial=portfolio');
      }, 1000);

      return () => clearTimeout(timer);
    }
  }, [startTutorial, router]);

  async function logout() {
    try {
      await apiFetch("/api/v1/auth/logout", { method: "POST" });
    } finally {
      window.location.href = "/login";
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside
        className={[
          "sticky top-0 h-screen shrink-0 border-r border-white/10 bg-white/5 backdrop-blur",
          "transition-all duration-200 ease-out",
          collapsed ? "w-20" : "w-72",
        ].join(" ")}
      >
        <div className="h-full flex flex-col">
          {/* Brand / Toggle */}
          <div className="flex items-center justify-between gap-3 px-4 py-4 border-b border-white/10">
            <div className="min-w-0">
              <div className="text-xs text-white/60">Advisor Dashboard</div>
              <div className={collapsed ? "hidden" : "text-sm font-semibold tracking-tight"}>
                Admin Console
              </div>
            </div>

            <button
              onClick={() => setCollapsed((v) => !v)}
              className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs hover:bg-white/10"
              aria-label="Toggle sidebar"
              title="Toggle sidebar"
            >
              {collapsed ? "→" : "←"}
            </button>
          </div>

          {/* Nav */}
          <nav className="px-3 py-3 flex-1">
            <div className={collapsed ? "px-2 py-2 text-[10px] text-white/40" : "px-2 py-2 text-xs text-white/40"}>
              NAVIGATION
            </div>

            <div className="space-y-1">
              {nav.map((item) => {
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    id={item.id}
                    href={item.href}
                    className={[
                      "flex items-center gap-3 rounded-xl px-3 py-2 border transition-colors",
                      active
                        ? "bg-white text-black border-white"
                        : "bg-white/0 text-white border-white/0 hover:bg-white/10 hover:border-white/10",
                    ].join(" ")}
                  >
                    <span className={["h-2.5 w-2.5 rounded-full", active ? "bg-black" : "bg-white/40"].join(" ")} />
                    <span className={collapsed ? "hidden" : "text-sm"}>{item.label}</span>
                  </Link>
                );
              })}

              {/* Tutorial button */}
              <button
                id="tutorial-guide-button"
                onClick={() => startTutorial(FIRST_TIME_TUTORIAL_STEPS)}
                className="flex items-center gap-3 rounded-xl px-3 py-2 border bg-white/0 text-white border-white/0 hover:bg-white/10 hover:border-white/10 w-full"
              >
                <span className="h-2.5 w-2.5 rounded-full bg-white/40"></span>
                <span className={collapsed ? "hidden" : "text-sm"}>Tutorial Guide</span>
              </button>
            </div>
          </nav>

          {/* Logout at bottom */}
          <div className="px-3 pb-4">
            <button
              onClick={logout}
              className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm hover:bg-white/10"
            >
              {collapsed ? "⎋" : "Logout"}
            </button>
          </div>

          <div className="px-4 py-4 border-t border-white/10 text-xs text-white/50">
            <div className={collapsed ? "hidden" : "leading-relaxed"}>
              v1 • admin-only
              <br />
              Protected routes
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 min-w-0">{children}</main>
    </div>
  );
}