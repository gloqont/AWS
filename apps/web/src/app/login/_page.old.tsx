"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { apiFetch } from "@/lib/api";

const scenarios = [
  "What if interest rates spike by 2%?",
  "What if Tech sector crashes by 15%?",
  "What if GDP growth slows to 0.5%?",
  "What if oil prices surge to $120?",
  "What if inflation hits 8% this quarter?",
  "What if the Fed cuts rates by 50bps?",
];

const stats = [
  { label: "Portfolios Protected", target: 2400, prefix: "", suffix: "+", icon: "shield" },
  { label: "Assets Monitored", target: 12.4, prefix: "$", suffix: "B", icon: "chart" },
  { label: "AI Decisions / Day", target: 50000, prefix: "", suffix: "+", icon: "bolt" },
  { label: "Avg. Risk Reduction", target: 34, prefix: "", suffix: "%", icon: "arrow-down" },
];

const trustBadges = ["SOC2 Compliant", "Bank-Grade Encryption", "GDPR Ready", "99.99% Uptime"];

const particles = Array.from({ length: 25 }, (_, i) => ({
  id: i,
  left: `${Math.random() * 100}%`,
  top: `${Math.random() * 100}%`,
  size: 2 + Math.random() * 3,
  delay: Math.random() * 8,
  duration: 6 + Math.random() * 8,
  opacity: 0.15 + Math.random() * 0.3,
}));

function useCounter(target: number, duration = 2000, startDelay = 500) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    const timeout = setTimeout(() => {
      const steps = 60;
      const increment = target / steps;
      let current = 0;
      const interval = setInterval(() => {
        current += increment;
        if (current >= target) { setCount(target); clearInterval(interval); }
        else { setCount(Math.floor(current * 10) / 10); }
      }, duration / steps);
      return () => clearInterval(interval);
    }, startDelay);
    return () => clearTimeout(timeout);
  }, [target, duration, startDelay]);
  return count;
}

function Sparkline({ color = "#D4A853", delay = 0 }: { color?: string; delay?: number }) {
  const points = "0,30 15,25 30,28 45,15 55,20 70,8 85,12 100,5";
  return (
    <svg viewBox="0 0 100 35" className="w-full h-8" preserveAspectRatio="none">
      <defs>
        <linearGradient id={`grad-${color.replace('#', '')}`} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor={color} stopOpacity="0.2" />
          <stop offset="100%" stopColor={color} stopOpacity="0.8" />
        </linearGradient>
      </defs>
      <polyline fill="none" stroke={`url(#grad-${color.replace('#', '')})`} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" points={points} className="animate-draw-line" style={{ animationDelay: `${delay}ms` }} />
    </svg>
  );
}

function StatIcon({ type }: { type: string }) {
  const c = "w-5 h-5";
  switch (type) {
    case "shield": return <svg className={c} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>;
    case "chart": return <svg className={c} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" /></svg>;
    case "bolt": return <svg className={c} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>;
    case "arrow-down": return <svg className={c} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" /></svg>;
    default: return null;
  }
}

function StatCard({ stat, index }: { stat: typeof stats[0]; index: number }) {
  const value = useCounter(stat.target, 2000, 800 + index * 300);
  const displayValue = stat.target >= 1000
    ? stat.target >= 10000 ? `${(value / 1000).toFixed(value >= stat.target ? 0 : 1)}K` : value.toLocaleString(undefined, { maximumFractionDigits: 0 })
    : value % 1 !== 0 ? value.toFixed(1) : value.toString();
  return (
    <div className="animate-slide-up card-hover relative group/stat bg-white/[0.02] backdrop-blur-md border border-white/[0.05] rounded-xl p-4 overflow-hidden" style={{ animationDelay: `${0.6 + index * 0.15}s` }}>
      <div className="absolute inset-0 bg-gradient-to-br from-[#D4A853]/5 to-[#C9963B]/5 opacity-0 group-hover/stat:opacity-100 transition-opacity duration-500" />
      <div className="relative">
        <div className="flex items-center justify-between mb-2">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${index % 2 === 0 ? 'bg-[#D4A853]/10 text-[#D4A853]' : 'bg-[#8B8E94]/10 text-[#8B8E94]'}`}>
            <StatIcon type={stat.icon} />
          </div>
          <Sparkline color={index % 2 === 0 ? "#D4A853" : "#8B8E94"} delay={800 + index * 300} />
        </div>
        <div className="mt-2">
          <span className="text-2xl font-bold text-white tabular-nums">{stat.prefix}{displayValue}{stat.suffix}</span>
          <p className="text-xs text-white/35 mt-0.5">{stat.label}</p>
        </div>
      </div>
    </div>
  );
}

function FeatureCard({ title, desc, icon, color }: { title: string; desc: string; icon: React.ReactNode; color: string }) {
  return (
    <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.04] transition-colors hover:bg-white/[0.03]">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center mb-4 ${color} bg-opacity-10`}>{icon}</div>
      <h3 className="text-lg font-semibold text-white/90 mb-2">{title}</h3>
      <p className="text-sm text-white/40 leading-relaxed">{desc}</p>
    </div>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "/dashboard/portfolio-optimizer";
  const [email, setEmail] = useState("admin@admin.com");
  const [password, setPassword] = useState("admin123");
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [currentScenarioIndex, setCurrentScenarioIndex] = useState(0);
  const [displayText, setDisplayText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [typingSpeed, setTypingSpeed] = useState(80);
  const [showPassword, setShowPassword] = useState(false);
  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handleTyping = () => {
      const currentFullText = scenarios[currentScenarioIndex];
      if (isDeleting) { setDisplayText(currentFullText.substring(0, displayText.length - 1)); setTypingSpeed(40); }
      else { setDisplayText(currentFullText.substring(0, displayText.length + 1)); setTypingSpeed(80); }
      if (!isDeleting && displayText === currentFullText) { setTimeout(() => setIsDeleting(true), 2500); }
      else if (isDeleting && displayText === "") { setIsDeleting(false); setCurrentScenarioIndex((prev) => (prev + 1) % scenarios.length); }
    };
    const timer = setTimeout(handleTyping, typingSpeed);
    return () => clearTimeout(timer);
  }, [displayText, isDeleting, currentScenarioIndex, typingSpeed]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault(); setErr(null); setLoading(true);
    try {
      await apiFetch("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ username: email, password }) });
      localStorage.removeItem('hasCompletedTutorial_v2');
      setSuccess(true); setTimeout(() => router.push(next), 1200);
    } catch (e: any) { setErr(e.message || "Login failed"); }
    finally { setLoading(false); }
  }

  return (
    <div className="min-h-screen w-full bg-[#050505] text-white overflow-x-hidden relative selection:bg-[#D4A853]/30">

      {/* BACKGROUND */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute inset-0 animate-aurora opacity-20" style={{ background: 'linear-gradient(130deg, rgba(212,168,83,0.12) 0%, rgba(201,150,59,0.08) 25%, rgba(139,142,148,0.06) 50%, rgba(212,168,83,0.10) 75%, rgba(201,150,59,0.12) 100%)', backgroundSize: '400% 400%' }} />
        <div className="absolute -top-[30%] -left-[15%] w-[80%] h-[80%] bg-[#D4A853]/[0.04] rounded-full blur-[150px] animate-blob" />
        <div className="absolute top-[10%] -right-[15%] w-[70%] h-[70%] bg-[#C9963B]/[0.03] rounded-full blur-[150px] animate-blob animation-delay-2000" />
        <div className="absolute -bottom-[30%] left-[10%] w-[70%] h-[70%] bg-[#8B8E94]/[0.03] rounded-full blur-[150px] animate-blob animation-delay-4000" />
        <div className="absolute top-[50%] left-[40%] w-[40%] h-[40%] bg-[#D4A853]/[0.02] rounded-full blur-[120px] animate-breathe" />
        <div className="absolute inset-0 opacity-[0.015]" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noise\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noise)\'/%3E%3C/svg%3E")' }} />
        <div className="absolute inset-0 opacity-[0.02]" style={{ backgroundImage: `linear-gradient(rgba(212,168,83,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(212,168,83,0.03) 1px, transparent 1px)`, backgroundSize: '60px 60px' }} />
        {particles.map((p) => (
          <div key={p.id} className="absolute rounded-full animate-particle" style={{ left: p.left, top: p.top, width: p.size, height: p.size, background: `radial-gradient(circle, ${p.id % 3 === 0 ? 'rgba(212,168,83,0.7)' : p.id % 3 === 1 ? 'rgba(201,150,59,0.6)' : 'rgba(139,142,148,0.5)'}, transparent)`, animationDelay: `${p.delay}s`, animationDuration: `${p.duration}s`, opacity: p.opacity }} />
        ))}
      </div>

      {/* MAIN LAYOUT */}
      <div className="w-full max-w-[1600px] mx-auto grid grid-cols-1 lg:grid-cols-[1.3fr_1fr] relative z-10">

        {/* LEFT PANEL */}
        <div className="relative px-6 py-12 lg:px-16 lg:py-16 xl:px-24 flex flex-col gap-24 lg:gap-32">

          {/* HERO */}
          <div className="flex flex-col gap-8 min-h-[80vh] justify-center">
            <div className="animate-slide-up">
              <div className="flex items-center gap-3">
                <div className="relative group">
                  <div className="absolute -inset-1 bg-gradient-to-r from-[#D4A853] to-[#C9963B] rounded-xl blur opacity-30 group-hover:opacity-60 transition duration-500" />
                  <div className="relative w-10 h-10 rounded-xl bg-gradient-to-br from-[#D4A853] to-[#C9963B] flex items-center justify-center shadow-2xl">
                    <span className="font-bold text-xl text-[#050505]">G</span>
                  </div>
                </div>
                <span className="font-bold text-xl tracking-tight text-white/90">GLOQONT</span>
                <span className="ml-2 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest rounded-full bg-[#D4A853]/10 text-[#D4A853] border border-[#D4A853]/20">Beta</span>
              </div>
            </div>

            <div className="animate-slide-up" style={{ animationDelay: '0.2s' }}>
              <p className="text-sm font-semibold tracking-[0.2em] uppercase text-[#D4A853]/70 mb-4">Portfolio Risk Intelligence Platform</p>
              <h1 className="text-5xl xl:text-[4rem] font-bold leading-[1.1] tracking-tight">
                See the consequences of{" "}<br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#D4A853] via-[#C9963B] to-[#8B8E94] animate-gradient-text" style={{ backgroundSize: '200% auto' }}>your trade decisions.</span>
              </h1>
              <p className="mt-6 text-xl text-white/45 leading-relaxed max-w-xl">Analyse the consequences of your trade decisions before executing the trades.</p>
            </div>

            {/* Terminal */}
            <div className="animate-slide-up" style={{ animationDelay: '0.4s' }}>
              <div className="relative group max-w-xl">
                <div className="absolute -inset-0.5 bg-gradient-to-r from-[#D4A853]/15 to-[#8B8E94]/10 rounded-xl blur-sm opacity-50 group-hover:opacity-80 transition duration-700" />
                <div className="relative bg-[#0a0a0a]/80 backdrop-blur-xl border border-white/[0.05] rounded-xl overflow-hidden shadow-2xl">
                  <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/[0.03] bg-white/[0.01]">
                    <div className="flex gap-1.5">
                      <div className="w-2.5 h-2.5 rounded-full bg-[#D4A853]/60" />
                      <div className="w-2.5 h-2.5 rounded-full bg-[#8B8E94]/40" />
                      <div className="w-2.5 h-2.5 rounded-full bg-[#8B8E94]/25" />
                    </div>
                    <span className="text-[10px] text-white/15 ml-2 font-mono">gloqont-simulator — scenario-engine</span>
                  </div>
                  <div className="p-5 font-mono">
                    <div className="flex items-start gap-3 text-sm">
                      <span className="text-[#D4A853] mt-0.5 shrink-0">❯</span>
                      <div>
                        <span className="text-white/60">simulate</span>
                        <span className="text-[#D4A853] ml-2">--scenario</span>
                        <span className="text-white/80 ml-2">&quot;</span>
                        <span className="text-[#D4A853]/90">{displayText}</span>
                        <span className="inline-block w-0.5 h-4 ml-0.5 bg-[#D4A853] animate-pulse align-middle" />
                        <span className="text-white/80">&quot;</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>


          </div>



          {/* FEATURES */}
          <div className="space-y-8">
            <div className="space-y-2">
              <h2 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-white/50">Why leading advisors choose GLOQONT</h2>
              <p className="text-white/30">Institutional-grade tools for modern wealth management.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <FeatureCard title="Pre-trade Simulation" desc="Run scenarios like 'Interest Rates +2%' or 'Tech Crash' against your portfolio before trading." color="text-[#D4A853] bg-[#D4A853]" icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>} />
              <FeatureCard title="Tax Impact Analysis" desc="Automatically calculate STCG, LTCG, and hidden tax drags on every rebalance." color="text-[#C9963B] bg-[#C9963B]" icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>} />
              <FeatureCard title="Client-Ready Reports" desc="Generate white-labeled PDF reports explaining optimizations in plain english." color="text-[#8B8E94] bg-[#8B8E94]" icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>} />
            </div>
          </div>

          {/* HOW IT WORKS */}
          <div className="space-y-12 pb-24">
            <div className="space-y-2">
              <h2 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-white/50">From Chaos to Clarity</h2>
              <p className="text-white/30 max-w-lg">Turn market uncertainty into a calculated advantage with our 3-step intelligence framework.</p>
            </div>
            <div className="relative">
              <div className="absolute left-6 top-8 bottom-8 w-0.5 bg-gradient-to-b from-[#D4A853] via-[#C9963B] to-transparent opacity-25" />
              <div className="space-y-12">
                <div className="relative pl-20 group">
                  <div className="absolute left-3 top-0 w-6 h-6 rounded-full bg-[#050505] border-2 border-[#D4A853] z-10 flex items-center justify-center"><div className="w-2 h-2 rounded-full bg-[#D4A853] animate-pulse" /></div>
                  <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.04] backdrop-blur-sm hover:bg-white/[0.03] transition-all duration-500 hover:translate-x-2">
                    <span className="text-[#D4A853] text-xs font-bold tracking-wider uppercase mb-2 block">Step 01</span>
                    <h4 className="text-xl font-bold text-white mb-2">Import & Sync</h4>
                    <p className="text-white/35 leading-relaxed">Connect your brokerage account securely or upload a CSV. We instantly map your holdings to our global risk database.</p>
                  </div>
                </div>
                <div className="relative pl-20 group">
                  <div className="absolute left-3 top-0 w-6 h-6 rounded-full bg-[#050505] border-2 border-[#C9963B] z-10 flex items-center justify-center"><div className="w-2 h-2 rounded-full bg-[#C9963B]" /></div>
                  <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.04] backdrop-blur-sm hover:bg-white/[0.03] transition-all duration-500 hover:translate-x-2">
                    <span className="text-[#C9963B] text-xs font-bold tracking-wider uppercase mb-2 block">Step 02</span>
                    <h4 className="text-xl font-bold text-white mb-2">Stress Test</h4>
                    <p className="text-white/35 leading-relaxed">Select scenarios like &quot;Inflation Spike&quot; or &quot;Tech Crash&quot;. Watch as our engine simulates the impact on your specific positions.</p>
                  </div>
                </div>
                <div className="relative pl-20 group">
                  <div className="absolute left-3 top-0 w-6 h-6 rounded-full bg-[#050505] border-2 border-[#8B8E94] z-10 flex items-center justify-center"><div className="w-2 h-2 rounded-full bg-[#8B8E94] shadow-[0_0_10px_rgba(139,142,148,0.4)]" /></div>
                  <div className="p-6 rounded-2xl bg-gradient-to-br from-[#D4A853]/[0.06] to-transparent border border-[#D4A853]/15 backdrop-blur-sm transition-all duration-500 hover:translate-x-2 shadow-[0_0_30px_rgba(212,168,83,0.03)]">
                    <span className="text-[#D4A853] text-xs font-bold tracking-wider uppercase mb-2 block">Step 03</span>
                    <h4 className="text-xl font-bold text-white mb-2">Decision Intelligence</h4>
                    <p className="text-white/45 leading-relaxed">Review the consequences of your decisions. Optimize for tax efficiency and execute trades only when the odds are in your favor.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Trust Badges */}
          <div className="flex flex-wrap gap-3 pb-8">
            {trustBadges.map((badge) => (
              <div key={badge} className="flex items-center gap-1.5 px-3 py-1.5 bg-white/[0.02] border border-white/[0.04] rounded-full text-xs text-white/30 hover:text-white/50 hover:border-white/[0.08] transition-all duration-300">
                <svg className="w-3 h-3 text-[#D4A853]/50" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                {badge}
              </div>
            ))}
          </div>
        </div>

        {/* RIGHT PANEL: STICKY LOGIN */}
        <div className="relative hidden lg:block h-screen sticky top-0">
          <div className="flex items-center justify-center h-full px-8 xl:px-16 2xl:px-24">
            <div className="absolute left-0 top-[10%] bottom-[10%] w-px bg-gradient-to-b from-transparent via-white/[0.04] to-transparent" />
            <div className="w-full max-w-[420px] relative">
              <div className="relative animate-scale-in" style={{ animationDelay: '0.3s' }}>
                <div className="absolute -inset-[1px] rounded-2xl overflow-hidden">
                  <div className="absolute -inset-[100%] animate-rotate-glow" style={{ background: 'conic-gradient(from 0deg, transparent, rgba(212,168,83,0.35), transparent, rgba(139,142,148,0.15), transparent, rgba(201,150,59,0.3), transparent)' }} />
                </div>
                <div className="absolute inset-[1px] rounded-2xl bg-[#0a0a0a]" />

                <div className="relative bg-[#0a0a0a]/80 backdrop-blur-2xl rounded-2xl p-8 sm:p-9 shadow-2xl">
                  <div className="mb-8 animate-slide-up" style={{ animationDelay: '0.5s' }}>
                    <h2 className="text-2xl font-bold text-white">Welcome back</h2>
                    <p className="text-white/30 text-sm mt-1.5">Sign in to access your intelligence dashboard.</p>
                  </div>

                  <form onSubmit={onSubmit} className="space-y-5">
                    <div className="space-y-2 animate-slide-up" style={{ animationDelay: '0.6s' }}>
                      <label className="text-[11px] font-semibold text-white/40 uppercase tracking-[0.15em]">Email Address</label>
                      <div className="relative group/input">
                        <div className="absolute left-4 top-1/2 -translate-y-1/2 text-white/20 group-focus-within/input:text-[#D4A853] transition-colors duration-300">
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
                        </div>
                        <input ref={emailRef} className="input-premium w-full bg-white/[0.03] border border-white/[0.06] rounded-xl pl-11 pr-4 py-3.5 text-sm text-white placeholder-white/12 outline-none focus:border-[#D4A853]/35 focus:bg-[#D4A853]/[0.02] transition-all duration-300" value={email} onChange={(e) => setEmail(e.target.value)} type="email" autoComplete="email" placeholder="you@company.com" />
                      </div>
                    </div>

                    <div className="space-y-2 animate-slide-up" style={{ animationDelay: '0.7s' }}>
                      <label className="text-[11px] font-semibold text-white/40 uppercase tracking-[0.15em]">Password</label>
                      <div className="relative group/input">
                        <div className="absolute left-4 top-1/2 -translate-y-1/2 text-white/20 group-focus-within/input:text-[#D4A853] transition-colors duration-300">
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
                        </div>
                        <input ref={passwordRef} className="input-premium w-full bg-white/[0.03] border border-white/[0.06] rounded-xl pl-11 pr-12 py-3.5 text-sm text-white placeholder-white/12 outline-none focus:border-[#D4A853]/35 focus:bg-[#D4A853]/[0.02] transition-all duration-300" value={password} onChange={(e) => setPassword(e.target.value)} type={showPassword ? "text" : "password"} autoComplete="current-password" placeholder="••••••••" />
                        <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-4 top-1/2 -translate-y-1/2 text-white/20 hover:text-white/40 transition-colors duration-200">
                          {showPassword ? (
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" /></svg>
                          ) : (
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                          )}
                        </button>
                      </div>
                    </div>

                    {err && (
                      <div className="p-3.5 rounded-xl bg-red-500/[0.06] border border-red-500/12 text-red-400 text-sm flex items-center gap-2.5 animate-slide-up">
                        <div className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center shrink-0"><svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg></div>
                        <span>{err}</span>
                      </div>
                    )}

                    <div className="animate-slide-up" style={{ animationDelay: '0.8s' }}>
                      <button disabled={loading || success} className="btn-magnetic w-full relative overflow-hidden rounded-xl bg-gradient-to-r from-[#C9963B] via-[#D4A853] to-[#C9963B] text-[#050505] font-semibold py-4 shadow-lg shadow-[#D4A853]/15 hover:shadow-[#D4A853]/30 transition-all duration-500 disabled:opacity-60 disabled:cursor-not-allowed" style={{ backgroundSize: '200% auto' }} onMouseEnter={(e) => { (e.target as HTMLElement).style.backgroundPosition = 'right center'; }} onMouseLeave={(e) => { (e.target as HTMLElement).style.backgroundPosition = 'left center'; }}>
                        <div className="absolute inset-0 overflow-hidden rounded-xl"><div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/15 to-transparent animate-shimmer" style={{ animationDuration: '3s' }} /></div>
                        <span className="relative flex items-center justify-center gap-2.5 text-sm">
                          {success ? (<><svg className="w-5 h-5" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.5" className="opacity-30" /><path d="M8 12l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="animate-check" /></svg>Accessing Dashboard...</>) : loading ? (<><svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" /></svg>Authenticating...</>) : (<>Sign In to Dashboard<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" /></svg></>)}
                        </span>
                      </button>
                    </div>
                  </form>

                  <div className="mt-8 pt-6 border-t border-white/[0.03] animate-slide-up" style={{ animationDelay: '0.9s' }}>
                    <div className="flex items-center justify-center gap-5">
                      <div className="flex items-center gap-1.5 text-white/15 hover:text-white/30 transition-colors"><svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg><span className="text-[10px] font-medium">256-bit SSL</span></div>
                      <div className="w-px h-3 bg-white/[0.06]" />
                      <div className="flex items-center gap-1.5 text-white/15 hover:text-white/30 transition-colors"><svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg><span className="text-[10px] font-medium">SOC2</span></div>
                      <div className="w-px h-3 bg-white/[0.06]" />
                      <div className="flex items-center gap-1.5 text-white/15 hover:text-white/30 transition-colors"><svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg><span className="text-[10px] font-medium">GDPR</span></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Mobile Form */}
        <div className="lg:hidden px-6 pb-20">
          <div className="w-full max-w-md mx-auto relative group">
            <div className="absolute -inset-0.5 bg-gradient-to-r from-[#D4A853]/15 to-[#8B8E94]/10 rounded-xl blur-sm opacity-50 group-hover:opacity-80 transition duration-700"></div>
            <div className="relative bg-[#0a0a0a] border border-white/[0.06] rounded-xl p-6">
              <form onSubmit={onSubmit} className="space-y-4">
                <h3 className="text-lg font-bold text-white mb-4">Sign In</h3>
                <input className="w-full bg-white/5 border border-white/[0.06] rounded-lg px-4 py-3 text-white outline-none focus:border-[#D4A853]/40" value={email} onChange={(e) => setEmail(e.target.value)} type="email" placeholder="Email" />
                <input className="w-full bg-white/5 border border-white/[0.06] rounded-lg px-4 py-3 text-white outline-none focus:border-[#D4A853]/40" value={password} onChange={(e) => setPassword(e.target.value)} type="password" placeholder="Password" />
                {err && <p className="text-red-400 text-sm">{err}</p>}
                <button className="w-full bg-gradient-to-r from-[#C9963B] to-[#D4A853] rounded-lg py-3 font-medium text-[#050505] shadow-lg shadow-[#D4A853]/15">Sign In</button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
