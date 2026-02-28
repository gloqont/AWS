"use client";

import { motion } from "framer-motion";
import { useState, useEffect } from "react";

const scenarios = [
    "What if interest rates spike?",
    "What if tech crashes by 2%?",
    "What if Fed rates cut by 50bps?",
    "What if GDP growth slows to 0.5%?",
    "What if I buy Apple stock after 5 days?"
];

export function ActBifurcation() {
    const [text, setText] = useState("");
    const [index, setIndex] = useState(0);
    const [subIndex, setSubIndex] = useState(0);
    const [reverse, setReverse] = useState(false);
    const [blink, setBlink] = useState(true);

    // Blinking cursor effect
    useEffect(() => {
        const timeout2 = setInterval(() => {
            setBlink((prev) => !prev);
        }, 500);
        return () => clearInterval(timeout2);
    }, []);

    // Typing effect
    useEffect(() => {
        if (index >= scenarios.length) {
            setIndex(0);
            return;
        }

        if (subIndex === scenarios[index].length + 1 && !reverse) {
            const timeout = setTimeout(() => {
                setReverse(true);
            }, 1500); // Wait 1.5s before deleting
            return () => clearTimeout(timeout);
        }

        if (subIndex === 0 && reverse) {
            setReverse(false);
            setIndex((prev) => (prev + 1) % scenarios.length);
            return;
        }

        const timeout = setTimeout(() => {
            setSubIndex((prev) => prev + (reverse ? -1 : 1));
            setText(scenarios[index].substring(0, subIndex));
        }, reverse ? 30 : 60); // Delete fast, type normal

        return () => clearTimeout(timeout);
    }, [subIndex, index, reverse]);

    return (
        <section className="h-screen w-full flex flex-col items-center justify-center relative z-10 pointer-events-none">
            <div className="max-w-6xl text-center px-6 space-y-16">
                <motion.h2
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    transition={{ duration: 1 }}
                    className="text-5xl md:text-7xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white via-white/80 to-white/20"
                >
                    One trade. <br /> Infinite outcomes.
                </motion.h2>

                <div className="h-32 flex items-center justify-center">
                    <div className="bg-black/40 backdrop-blur-md border border-white/10 rounded-xl px-8 py-6 shadow-2xl">
                        <p className="text-xl md:text-4xl font-mono text-[#D4A853] min-w-[300px] md:min-w-[600px] flex items-center justify-center">
                            <span className="opacity-50 mr-3">{">"}</span>
                            {text}
                            <span className={`ml-1 w-3 h-8 bg-[#D4A853] ${blink ? "opacity-100" : "opacity-0"}`} />
                        </p>
                    </div>
                </div>
            </div>
        </section>
    );
}
