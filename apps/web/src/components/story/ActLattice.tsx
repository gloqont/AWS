"use client";

import { motion } from "framer-motion";

export function ActLattice() {
    return (
        <section className="h-screen w-full flex flex-col items-center justify-center relative z-10 pointer-events-none">
            <div className="max-w-5xl text-center px-6">
                <motion.div
                    initial={{ opacity: 0, scale: 2, filter: "blur(20px)" }}
                    whileInView={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
                    transition={{ duration: 1.2, ease: "circOut" }}
                >
                    <h2 className="text-5xl md:text-7xl font-bold text-white mb-6 tracking-tight">
                        CRYSTALLIZE <br /> <span className="text-[#D4A853]">THE FUTURE</span>
                    </h2>
                </motion.div>

                <motion.p
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    transition={{ duration: 1, delay: 0.5 }}
                    className="text-white/40 text-lg md:text-xl font-light"
                >
                    Observation collapses probability into profit.
                </motion.p>
            </div>
        </section>
    );
}
