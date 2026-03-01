"use client";

import { motion } from "framer-motion";

export function ActGravity() {
    return (
        <section className="h-screen w-full flex flex-col items-center justify-center relative z-10 pointer-events-none">
            <div className="max-w-4xl text-center px-6 space-y-8">
                <motion.h2
                    initial={{ opacity: 0, scale: 0.8 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 1 }}
                    className="text-6xl md:text-8xl font-bold text-transparent bg-clip-text bg-gradient-to-b from-white/10 to-white/0"
                >
                    MAXIMUM DRAG
                </motion.h2>

                <motion.p
                    initial={{ opacity: 0, y: 50 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.2 }}
                    className="text-xl md:text-3xl text-red-500/80 font-mono tracking-widest"
                >
                    INEFFICIENCY IS A BLACK HOLE.
                </motion.p>

                <motion.div
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    transition={{ duration: 1, delay: 0.5 }}
                    className="text-sm text-white/30 max-w-lg mx-auto"
                >
                    <p>Taxes. Slippage. Emotional Bias. <br /> They warp your trajectory.</p>
                </motion.div>
            </div>
        </section>
    );
}
