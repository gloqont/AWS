"use client";

import { motion } from "framer-motion";

const steps = [
    {
        id: 1,
        title: "Connect",
        desc: "Sync your portfolio into GLOQONT's system.",
        icon: (
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg>
        )
    },
    {
        id: 2,
        title: "Stress Test in Real Time",
        desc: "GLOQONT stress tests your portfolio against live regimes, quantifying downside, volatility, drawdown, and capital fragility instantly.",
        icon: (
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.384-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" /></svg>
        )
    },
    {
        id: 3,
        title: "See the Full Consequence",
        desc: "Analyze risk and tax impact together, so every trade decision is evaluated on after-tax outcomes, not just pre-tax returns.",
        icon: (
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>
        )
    }
];

export function ActSteps() {
    return (
        <section className="h-screen w-full flex flex-col items-center justify-center relative z-10 pointer-events-none">
            <div className="max-w-6xl w-full px-6 grid grid-cols-1 md:grid-cols-3 gap-8 pointer-events-auto">
                {steps.map((step, i) => (
                    <motion.div
                        key={step.id}
                        initial={{ opacity: 0, y: 50 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.8, delay: i * 0.2 }}
                        className="group relative bg-black/40 backdrop-blur-xl border border-white/10 rounded-2xl p-8 hover:border-[#D4A853]/50 transition-all duration-500 hover:-translate-y-2 hover:shadow-[0_0_30px_rgba(212,168,83,0.1)]"
                    >
                        <div className="absolute top-0 right-0 p-4 opacity-20 text-6xl font-bold bg-clip-text text-transparent bg-gradient-to-b from-white to-white/0 font-mono select-none">
                            0{step.id}
                        </div>

                        <div className="w-12 h-12 rounded-lg bg-white/5 flex items-center justify-center text-[#D4A853] mb-6 group-hover:bg-[#D4A853] group-hover:text-black transition-colors duration-300">
                            {step.icon}
                        </div>

                        <h3 className="text-2xl font-bold text-white mb-3 tracking-wide">{step.title}</h3>
                        <p className="text-white/60 leading-relaxed font-light">{step.desc}</p>

                        {/* Hover Glow */}
                        <div className="absolute -inset-0.5 bg-gradient-to-r from-[#D4A853] to-transparent opacity-0 group-hover:opacity-20 rounded-2xl blur transition duration-500 -z-10" />
                    </motion.div>
                ))}
            </div>

            <motion.div
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                transition={{ delay: 1, duration: 1 }}
                className="mt-16 text-white/40 font-mono text-sm"
            >
                SYSTEM ONLINE · AWAITING INPUT
            </motion.div>
        </section>
    );
}
