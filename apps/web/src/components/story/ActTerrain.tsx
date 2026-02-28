"use client";

import { motion } from "framer-motion";

export function ActTerrain() {
    return (
        <section className="h-screen w-full flex flex-col items-center justify-center relative z-10 pointer-events-none">
            <div className="w-full h-full relative">
                {/* Floating labels for the 3D Terrain */}

                <motion.div
                    initial={{ opacity: 0, x: -50 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.8 }}
                    className="absolute top-1/4 left-10 md:left-20"
                >
                    <div className="flex items-center gap-3">
                        <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse shadow-[0_0_10px_rgba(239,68,68,0.5)]" />
                        <span className="text-sm font-mono text-red-400">RISK DETECTED</span>
                    </div>
                    <p className="text-white/30 text-xs mt-1 max-w-[150px]">High volatility zone identified in Tech Sector.</p>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, x: 50 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.8, delay: 0.3 }}
                    className="absolute bottom-1/3 right-10 md:right-20 text-right"
                >
                    <div className="flex items-center gap-3 justify-end">
                        <span className="text-sm font-mono text-[#D4A853]">OPPORTUNITY</span>
                        <div className="w-3 h-3 rounded-full bg-[#D4A853] animate-pulse shadow-[0_0_10px_rgba(212,168,83,0.5)]" />
                    </div>
                    <p className="text-white/30 text-xs mt-1 max-w-[150px] ml-auto">Tax-efficient entry point found.</p>
                </motion.div>
            </div>
        </section>
    );
}
