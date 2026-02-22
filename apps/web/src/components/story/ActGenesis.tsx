"use client";

import { motion } from "framer-motion";

export function ActGenesis() {
    return (
        <section className="h-screen w-full flex flex-col items-center justify-center relative z-10 pointer-events-none">
            {/* The text "INTRODUCING GLOQONT" is rendered by the Canvas, 
          so this component mainly handles the subtext. */}

            <div className="absolute bottom-24 w-full text-center px-6">
                <motion.p
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    transition={{ duration: 1, delay: 0.5 }}
                    className="text-xl md:text-2xl text-white/60 font-light tracking-wide max-w-2xl mx-auto"
                >
                    Analyse the consequences of your trade decisions <br />
                    <span className="text-[#D4A853]">before executing them.</span>
                </motion.p>
            </div>
        </section>
    );
}
