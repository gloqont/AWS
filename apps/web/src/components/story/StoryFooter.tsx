"use client";

import { motion } from "framer-motion";

const TRUST_BADGES = [
    {
        icon: "🔒",
        title: "Bank-Grade Encryption",
        desc: "256-bit AES encryption for all data in transit and at rest.",
    },
    {
        icon: "🛡️",
        title: "Privacy First",
        desc: "We never sell your data. Your portfolio stays yours.",
    },
    {
        icon: "📊",
        title: "Read-Only Analysis",
        desc: "GLOQONT only reads market data. We never execute trades on your behalf.",
    },
    {
        icon: "🔐",
        title: "SOC 2 Aligned",
        desc: "Infrastructure designed to meet enterprise-grade compliance standards.",
    },
];

const FOOTER_LINKS = [
    { label: "Pricing", href: "/pricing" },
    { label: "Privacy Policy", href: "/privacy" },
    { label: "Terms of Service", href: "/terms" },
    { label: "Security", href: "#" },
    { label: "Data Processing", href: "#" },
];

export function StoryFooter() {
    return (
        <footer className="relative z-20 pointer-events-auto bg-gradient-to-b from-transparent via-[#050505] to-[#050505]">
            {/* Trust Badges */}
            <div className="max-w-5xl mx-auto px-6 pt-24 pb-16">
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6 }}
                    className="text-center mb-12"
                >
                    <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-[#D4A853]/20 bg-[#D4A853]/5 mb-4">
                        <span className="h-1.5 w-1.5 rounded-full bg-green-400 animate-pulse" />
                        <span className="text-[10px] uppercase tracking-[0.2em] text-[#D4A853]/80 font-mono">
                            Infrastructure Secure
                        </span>
                    </div>
                    <h3 className="text-xl font-semibold text-white/90">Your data. Your decisions. Your control.</h3>
                    <p className="text-sm text-white/40 mt-2 max-w-lg mx-auto">
                        GLOQONT is built with institutional-grade security principles. We analyze scenarios — we never touch your funds.
                    </p>
                </motion.div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {TRUST_BADGES.map((badge, i) => (
                        <motion.div
                            key={badge.title}
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.5, delay: i * 0.1 }}
                            className="group rounded-xl border border-white/5 bg-white/[0.02] backdrop-blur p-5 hover:border-[#D4A853]/20 hover:bg-[#D4A853]/[0.03] transition-all duration-300"
                        >
                            <div className="text-2xl mb-3">{badge.icon}</div>
                            <div className="text-sm font-medium text-white/90 mb-1">{badge.title}</div>
                            <div className="text-xs text-white/40 leading-relaxed">{badge.desc}</div>
                        </motion.div>
                    ))}
                </div>
            </div>

            {/* Divider */}
            <div className="max-w-5xl mx-auto px-6">
                <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
            </div>

            {/* Bottom Bar */}
            <div className="max-w-5xl mx-auto px-6 py-8">
                <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <div className="h-6 w-6 rounded-md border border-[#D4A853]/30 bg-black/40 flex items-center justify-center">
                            <span className="text-[#D4A853] text-[10px] font-bold">G</span>
                        </div>
                        <span className="text-xs text-white/30">
                            © {new Date().getFullYear()} GLOQONT. All rights reserved.
                        </span>
                    </div>

                    <nav className="flex items-center gap-6">
                        {FOOTER_LINKS.map((link) => (
                            <a
                                key={link.label}
                                href={link.href}
                                className="text-xs text-white/30 hover:text-[#D4A853]/80 transition-colors"
                            >
                                {link.label}
                            </a>
                        ))}
                    </nav>
                </div>

                <div className="mt-6 text-center">
                    <p className="text-[10px] text-white/20 font-mono leading-relaxed max-w-2xl mx-auto">
                        GLOQONT provides analytical tools for educational and informational purposes only.
                        Nothing on this platform constitutes financial, tax, or investment advice.
                        Past performance does not guarantee future results. Consult a licensed professional before making investment decisions.
                    </p>
                </div>
            </div>
        </footer>
    );
}
