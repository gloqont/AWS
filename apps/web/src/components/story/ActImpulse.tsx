"use client";

import { motion } from "framer-motion";

export function ActImpulse() {
    return (
        <section className="h-screen w-full flex items-center justify-center relative z-10 pointer-events-none">
            <div className="max-w-2xl text-center px-6">
                <motion.p
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.2 }}
                    className="text-lg md:text-xl text-white/50 mb-4 font-light tracking-wide"
                >
                    The market is noisy.
                </motion.p>
                <motion.h2
                    initial={{ opacity: 0, scale: 0.9 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.8, delay: 0.4 }}
                    className="text-4xl md:text-6xl font-bold text-white tracking-tighter"
                >
                    Your intuition is <span className="text-white/20">quiet.</span>
                </motion.h2>
            </div>
        </section>
    );
}
