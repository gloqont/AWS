"use client";

import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import {
  TaxProfileWizard,
  JURISDICTIONS,
  COUNTRY_ACCOUNT_TYPES,
  DEFAULT_ACCOUNT_TYPES,
  getIncomeTiers,
} from "@/components/TaxProfileWizard";
import type { TaxProfile } from "@/components/TaxProfileWizard";
import OnboardingFlow from "@/components/onboarding/OnboardingFlow";

const nav = [
  { label: "Portfolio", href: "/dashboard/portfolio-optimizer", id: "portfolio-optimizer-link" },
  { label: "Scenario Simulation", href: "/dashboard/scenario-simulation", id: "scenario-simulation-link" },
  { label: "Tax Advisor", href: "/dashboard/tax-advisor", id: "tax-advisor-link" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [isTaxWizardOpen, setIsTaxWizardOpen] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [savedProfile, setSavedProfile] = useState<TaxProfile | null>(null);

  // Persist collapsed state
  useEffect(() => {
    const saved = localStorage.getItem("sidebar_collapsed");
    if (saved) setCollapsed(saved === "1");
  }, []);
  useEffect(() => {
    localStorage.setItem("sidebar_collapsed", collapsed ? "1" : "0");
  }, [collapsed]);

  // Onboarding Flow
  const [showOnboarding, setShowOnboarding] = useState(true);

  // Load theme preference
  useEffect(() => {
    const theme = localStorage.getItem("theme_preference");
    if (theme === "light") {
      document.documentElement.classList.add("theme-light");
    } else {
      document.documentElement.classList.remove("theme-light");
    }
  }, []);

  // Check if we need to show settings/profile updates
  // Re-read on wizard close, on pathname change, and poll for questionnaire updates
  useEffect(() => {
    const loadProfile = () => {
      const raw = localStorage.getItem("gloqont_tax_profile");
      if (raw) {
        try {
          setSavedProfile(JSON.parse(raw));
        } catch {
          // ignore
        }
      } else {
        setSavedProfile(null);
      }
    };
    loadProfile();

    // Poll every 2s to catch questionnaire updates
    const interval = setInterval(loadProfile, 2000);
    // Also listen for focus (user returns to tab)
    window.addEventListener("focus", loadProfile);
    return () => {
      clearInterval(interval);
      window.removeEventListener("focus", loadProfile);
    };
  }, [isTaxWizardOpen, pathname]); // Reload when wizard closes or page changes

  async function logout() {
    try {
      await apiFetch("/api/v1/auth/logout", { method: "POST" });
    } finally {
      // Clear auth-related and session-specific state on logout
      // Note: gloqont_user_profile is kept across logouts (it's preferences, not auth)
      localStorage.removeItem("hasCompletedTutorial_v2");
      localStorage.removeItem("gloqont_tax_profile");
      localStorage.removeItem("portfolio_rows");
      localStorage.removeItem("portfolio_name");
      localStorage.removeItem("portfolio_risk");

      sessionStorage.removeItem("tutorialShownThisSession");
      sessionStorage.removeItem("gloqont_onboarding_shown"); // Clear this so it shows again on next login

      window.location.href = "/login";
    }
  }

  const handleWizardComplete = (profile: TaxProfile) => {
    setSavedProfile(profile);
    setIsTaxWizardOpen(false);
  };

  const resetProfile = () => {
    localStorage.removeItem("gloqont_tax_profile");
    localStorage.removeItem("gloqont_user_profile");
    localStorage.removeItem("hasCompletedTutorial_v2");
    sessionStorage.removeItem("tutorialShownThisSession");
    sessionStorage.removeItem("gloqont_onboarding_shown");
    setSavedProfile(null);
    setShowSettings(false);
    setIsTaxWizardOpen(true);
  };

  const accountTypes = savedProfile
    ? (COUNTRY_ACCOUNT_TYPES[savedProfile.taxCountry] || DEFAULT_ACCOUNT_TYPES)
    : {};

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside
        className={[
          "sticky top-0 h-screen shrink-0 border-r border-[#D4A853]/20 bg-black/20 backdrop-blur-xl",
          "transition-all duration-200 ease-out shadow-2xl",
          collapsed ? "w-20" : "w-72",
        ].join(" ")}
      >
        <div className="h-full flex flex-col">
          {/* Brand / Toggle */}
          <div className="flex items-center justify-between gap-3 px-4 py-4 border-b border-white/10">
            <div className={["flex items-center min-w-0", collapsed ? "gap-0" : "gap-3"].join(" ")}>
              <div
                className={[
                  "h-10 w-10 rounded-xl border border-[#D4A853]/30 bg-black/40 flex items-center justify-center shadow-[0_0_10px_rgba(212,168,83,0.1)]",
                  "overflow-hidden",
                ].join(" ")}
              >
                <picture className="h-full w-full">
                  <source srcSet="/branding/gloqont-logo.svg" type="image/svg+xml" />
                  <img
                    src="/branding/gloqont-logo.png"
                    alt="GLOQONT logo"
                    className="h-full w-full object-cover"
                  />
                </picture>
              </div>
              <div className={collapsed ? "hidden" : "min-w-0"}>
                <div className="text-xs text-white/60">GLOQONT</div>
                <div className="text-sm font-semibold tracking-tight">Advisor Console</div>
              </div>
            </div>

            <button
              onClick={() => setCollapsed((v) => !v)}
              className={[
                "rounded-xl border border-white/10 bg-white/5 hover:bg-white/10",
                collapsed ? "px-2.5 py-2 text-xs" : "px-3 py-2 text-xs",
              ].join(" ")}
              aria-label="Toggle sidebar"
              title="Toggle sidebar"
            >
              {collapsed ? "→" : "←"}
            </button>
          </div>

          {/* Nav */}
          <nav className="px-3 py-3 flex-1">
            <div className={collapsed ? "hidden" : "px-2 py-2 text-xs text-white/40"}>
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
                      "flex items-center rounded-xl border transition-colors",
                      collapsed ? "justify-center px-2 py-2" : "gap-3 px-3 py-2",
                      active
                        ? "bg-[#D4A853] text-black border-[#D4A853] shadow-[0_0_15px_rgba(212,168,83,0.3)]"
                        : "bg-white/0 text-white border-white/0 hover:bg-white/5 hover:border-[#D4A853]/30 hover:text-[#D4A853]",
                    ].join(" ")}
                  >
                    <span className={["h-2.5 w-2.5 rounded-full shadow-[0_0_5px_currentColor]", active ? "bg-black" : "bg-white/20"].join(" ")} />
                    <span className={collapsed ? "hidden" : "text-sm font-medium"}>{item.label}</span>
                  </Link>
                );
              })}

              {/* Guide Button */}
              <button
                onClick={() => {
                  localStorage.removeItem("hasCompletedTutorial_v2");
                  sessionStorage.removeItem("tutorialShownThisSession");
                  window.location.href = "/dashboard/portfolio-optimizer?tutorial=portfolio";
                }}
                className={[
                  "flex w-full items-center rounded-xl border transition-colors",
                  collapsed ? "justify-center px-2 py-2" : "gap-3 px-3 py-2",
                  "bg-white/0 text-white border-white/0 hover:bg-white/10 hover:border-white/10",
                ].join(" ")}
              >
                <span className="h-2.5 w-2.5 rounded-full bg-blue-400/40" />
                <span className={collapsed ? "hidden" : "text-sm"}>Guide</span>
              </button>

            </div>
          </nav>

          {/* Bottom Section — Settings + Theme + Logout */}
          <div className={collapsed ? "px-3 pb-4 flex flex-col items-center gap-2" : "px-3 pb-4 space-y-2"}>

            {/* ⚙ Settings Button */}
            <button
              onClick={() => setShowSettings(!showSettings)}
              className={[
                "rounded-xl border transition-colors",
                collapsed ? "h-10 w-10 text-sm border-white/10 bg-white/5 hover:bg-white/10" : "w-full px-3 py-2 text-sm text-left flex items-center gap-2",
                showSettings
                  ? "bg-[#D4A853]/10 border-[#D4A853]/30 text-[#D4A853]"
                  : "border-white/10 bg-white/5 hover:bg-white/10 hover:border-[#D4A853]/30 hover:text-[#D4A853]",
              ].join(" ")}
              title="Tax Settings"
            >
              {collapsed ? "⚙" : (
                <>
                  <span>⚙</span>
                  <span>Tax Settings</span>
                </>
              )}
            </button>

            {/* Settings Panel (expandable) */}
            {showSettings && !collapsed && (
              <div className="rounded-xl border border-[#D4A853]/20 bg-black/40 p-3 space-y-2 animate-in fade-in slide-in-from-bottom-2 duration-200">
                {savedProfile ? (
                  <>
                    <div className="text-xs text-[#D4A853]/60 uppercase tracking-wider mb-1">Your Tax Profile</div>
                    <div className="flex justify-between text-xs">
                      <span className="text-white/50">Country</span>
                      <span className="text-white">{JURISDICTIONS[savedProfile.taxCountry]?.flag} {JURISDICTIONS[savedProfile.taxCountry]?.label}</span>
                    </div>
                    {savedProfile.taxSubJurisdiction && (
                      <div className="flex justify-between text-xs">
                        <span className="text-white/50">State</span>
                        <span className="text-white">{savedProfile.taxSubJurisdiction}</span>
                      </div>
                    )}
                    <div className="flex justify-between text-xs">
                      <span className="text-white/50">Account</span>
                      <span className="text-white text-right max-w-[120px] truncate">{accountTypes[savedProfile.taxAccountType] || savedProfile.taxAccountType}</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-white/50">Income</span>
                      <span className="text-white">{getIncomeTiers(savedProfile.taxCountry)[savedProfile.taxIncomeTier] || savedProfile.taxIncomeTier}</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-white/50">Filing</span>
                      <span className="text-white capitalize">{savedProfile.taxFilingStatus?.replace("_", " ")}</span>
                    </div>
                    <button
                      onClick={resetProfile}
                      className="w-full mt-2 px-3 py-1.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs hover:bg-red-500/20 transition"
                    >
                      Reset & Reconfigure
                    </button>
                  </>
                ) : (
                  <div className="text-center py-2">
                    <p className="text-white/40 text-xs mb-2">No profile configured</p>
                    <button
                      onClick={() => { setShowSettings(false); setIsTaxWizardOpen(true); }}
                      className="px-3 py-1.5 rounded-lg bg-[#D4A853]/10 border border-[#D4A853]/20 text-[#D4A853] text-xs hover:bg-[#D4A853]/20 transition"
                    >
                      Set Up Now
                    </button>
                  </div>
                )}
              </div>
            )}

            <button
              onClick={() => {
                const html = document.documentElement;
                if (html.classList.contains("theme-light")) {
                  html.classList.remove("theme-light");
                  localStorage.setItem("theme_preference", "dark");
                } else {
                  html.classList.add("theme-light");
                  localStorage.setItem("theme_preference", "light");
                }
              }}
              className={[
                "rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 hover:border-[#D4A853]/30 hover:text-[#D4A853] transition-colors",
                collapsed ? "h-10 w-10 text-sm" : "w-full px-3 py-2 text-sm",
              ].join(" ")}
              title="Toggle Theme"
            >
              {collapsed ? "◑" : "Toggle Theme"}
            </button>
            <button
              onClick={logout}
              className={[
                "rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 hover:border-red-500/30 hover:text-red-400 transition-colors",
                collapsed ? "h-10 w-10 text-sm" : "w-full px-3 py-2 text-sm",
              ].join(" ")}
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

      {/* Global Tax Wizard */}
      <TaxProfileWizard
        isOpen={isTaxWizardOpen}
        onComplete={handleWizardComplete}
        onClose={() => setIsTaxWizardOpen(false)}
      />

      {/* New Onboarding Flow (Questionnaire + Tax + Tutorial Trigger) */}
      <OnboardingFlow />
    </div>
  );
}
