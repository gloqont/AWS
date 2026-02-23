"use client";

import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";

export function ActLogin() {
    const params = useSearchParams();
    const next = params.get("next") || "/dashboard/portfolio-optimizer";

    const signInHref = `/api/v1/auth/login?next=${encodeURIComponent(next)}`;
    const signUpHref = `/api/v1/auth/login?mode=signup&next=${encodeURIComponent(next)}`;

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
                        <p className="text-[#D4A853]/60 text-xs font-mono mt-2">SYSTEM READY // SECURE AUTH VIA COGNITO</p>
                    </div>

                    <div className="space-y-4">
                        <p className="text-white/70 text-sm leading-relaxed">
                            Continue to secure sign-in. You will be redirected to our identity provider and returned here after authentication.
                        </p>

                        <a
                            href={signInHref}
                            className="block w-full text-center bg-[#D4A853] hover:bg-[#C9963B] text-black font-bold py-4 rounded-lg shadow-[0_0_20px_rgba(212,168,83,0.2)] hover:shadow-[0_0_30px_rgba(212,168,83,0.4)] transition-all uppercase tracking-widest text-sm"
                        >
                            Engage System
                        </a>

                        <p className="text-center text-xs text-white/60">
                            Don&apos;t have an account?{" "}
                            <a
                                href={signUpHref}
                                className="text-[#D4A853] hover:text-[#e0b869] underline underline-offset-4"
                            >
                                Create one
                            </a>
                        </p>

                        <div className="text-center">
                            <Link href="/signup" className="text-[11px] text-white/45 hover:text-white/65">
                                Need help? Open account setup page
                            </Link>
                        </div>
                    </div>

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
