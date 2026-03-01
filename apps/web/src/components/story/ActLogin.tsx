"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { apiFetch } from "@/lib/api";

export function ActLogin() {
    const router = useRouter();
    const params = useSearchParams();
    const next = params.get("next") || "/dashboard/portfolio-optimizer";
    const [email, setEmail] = useState("admin@admin.com");
    const [password, setPassword] = useState("admin123");
    const [err, setErr] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const [acceptedPrivacy, setAcceptedPrivacy] = useState(false);
    const [acceptedTerms, setAcceptedTerms] = useState(false);

    async function onSubmit(e: React.FormEvent) {
        e.preventDefault();
        setErr(null);
        setLoading(true);
        try {
            await apiFetch("/api/v1/auth/login", {
                method: "POST",
                body: JSON.stringify({ username: email, password }),
            });
            localStorage.removeItem("hasCompletedTutorial_v2");
            setSuccess(true);
            setTimeout(() => router.push(next), 1200);
        } catch (e: any) {
            setErr(e.message || "Login failed");
        } finally {
            setLoading(false);
        }
    }

    return (
        <section className="min-h-screen w-full flex flex-col items-center justify-center relative z-20 pointer-events-auto">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.8 }}
                className="w-full max-w-md relative"
            >
                {/* Cockpit / HUD Frame */}
                <div className="absolute -inset-1 bg-gradient-to-b from-[#D4A853]/20 to-transparent rounded-2xl blur-sm" />

                <div className="relative bg-[#0a0a0a]/90 backdrop-blur-xl border border-[#D4A853]/20 rounded-2xl p-8 shadow-2xl">
                    <div className="text-center mb-8">
                        <h2 className="text-2xl font-bold text-white tracking-widest uppercase">Command</h2>
                        <p className="text-[#D4A853]/60 text-xs font-mono mt-2">SYSTEM READY // AWAITING AUTH</p>
                    </div>

                    <form onSubmit={onSubmit} className="space-y-6">
                        <div className="space-y-2">
                            <label htmlFor="operatorIdInput" className="text-[10px] text-white/40 uppercase tracking-widest block">Identify</label>
                            <input
                                id="operatorIdInput"
                                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white outline-none focus:border-[#D4A853]/50 focus:bg-[#D4A853]/5 transition-all font-mono"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                type="email"
                                placeholder="OPERATOR ID"
                            />
                        </div>

                        <div className="space-y-2">
                            <label htmlFor="accessKeyInput" className="text-[10px] text-white/40 uppercase tracking-widest block">Key</label>
                            <div className="relative">
                                <input
                                    id="accessKeyInput"
                                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white outline-none focus:border-[#D4A853]/50 focus:bg-[#D4A853]/5 transition-all font-mono"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    type={showPassword ? "text" : "password"}
                                    placeholder="ACCESS KEY"
                                />
                                <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-4 top-1/2 -translate-y-1/2 text-white/20 hover:text-white/50">
                                    {showPassword ? "HIDE" : "SHOW"}
                                </button>
                            </div>
                        </div>

                        {err && (
                            <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-mono">
                                ERROR: {err}
                            </div>
                        )}

                        <div className="space-y-4">
                            <label className="flex items-start space-x-3 cursor-pointer group">
                                <div className="relative flex items-start mt-0.5">
                                    <input
                                        type="checkbox"
                                        className="peer appearance-none w-5 h-5 border border-white/20 rounded bg-white/5 checked:bg-[#D4A853]/20 checked:border-[#D4A853] transition-all cursor-pointer"
                                        checked={acceptedPrivacy}
                                        onChange={e => setAcceptedPrivacy(e.target.checked)}
                                    />
                                    <div className="absolute inset-0 flex items-center justify-center opacity-0 peer-checked:opacity-100 pointer-events-none text-[#D4A853]">
                                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                        </svg>
                                    </div>
                                </div>
                                <span className="text-white/70 text-xs font-mono group-hover:text-white/90 transition-colors">I accept the Privacy & Safety Policy</span>
                            </label>
                            <label className="flex items-start space-x-3 cursor-pointer group">
                                <div className="relative flex items-start mt-0.5">
                                    <input
                                        type="checkbox"
                                        className="peer appearance-none w-5 h-5 border border-white/20 rounded bg-white/5 checked:bg-[#D4A853]/20 checked:border-[#D4A853] transition-all cursor-pointer"
                                        checked={acceptedTerms}
                                        onChange={e => setAcceptedTerms(e.target.checked)}
                                    />
                                    <div className="absolute inset-0 flex items-center justify-center opacity-0 peer-checked:opacity-100 pointer-events-none text-[#D4A853]">
                                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                        </svg>
                                    </div>
                                </div>
                                <span className="text-white/70 text-xs font-mono group-hover:text-white/90 transition-colors">I agree to the Terms of Service & Conditions</span>
                            </label>
                        </div>

                        <button
                            disabled={loading || success || !acceptedPrivacy || !acceptedTerms}
                            className="w-full bg-[#D4A853] hover:bg-[#C9963B] text-black font-bold py-4 rounded-lg shadow-[0_0_20px_rgba(212,168,83,0.2)] hover:shadow-[0_0_30px_rgba(212,168,83,0.4)] transition-all disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-widest text-sm"
                        >
                            {loading ? "INITIALIZING..." : success ? "ACCESS GRANTED" : "ENGAGE SYSTEM"}
                        </button>
                    </form>

                    {/* Decorative HUD Details */}
                    <div className="absolute top-0 left-0 w-4 h-4 border-t border-l border-[#D4A853]/50 -mt-1 -ml-1" />
                    <div className="absolute top-0 right-0 w-4 h-4 border-t border-r border-[#D4A853]/50 -mt-1 -mr-1" />
                    <div className="absolute bottom-0 left-0 w-4 h-4 border-b border-l border-[#D4A853]/50 -mb-1 -ml-1" />
                    <div className="absolute bottom-0 right-0 w-4 h-4 border-b border-r border-[#D4A853]/50 -mb-1 -mr-1" />
                </div>
            </motion.div>
        </section>
    );
}
