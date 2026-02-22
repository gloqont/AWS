"use client";

import { useRef } from "react";
import { useScroll, useTransform } from "framer-motion";
import { StoryCanvas } from "./StoryCanvas";
import { ActImpulse } from "./ActImpulse";
import { ActBifurcation } from "./ActBifurcation";
import { ActGenesis } from "./ActGenesis";
import { ActSteps } from "./ActSteps";
import { ActTerrain } from "./ActTerrain";
import { ActLogin } from "./ActLogin";

export default function StoryLayout() {
    const containerRef = useRef<HTMLDivElement>(null);
    const { scrollYProgress } = useScroll({
        target: containerRef,
        offset: ["start start", "end end"]
    });

    return (
        <div ref={containerRef} className="relative bg-[#050505] text-white">
            {/* Sticky Background Canvas */}
            <div className="sticky top-0 h-screen w-full overflow-hidden">
                <StoryCanvas scrollProgress={scrollYProgress} />
            </div>

            {/* Scrolling Content Acts */}
            <div className="relative z-10 -mt-[100vh]">
                <div className="h-screen w-full"><ActImpulse /></div>
                <div className="h-screen w-full"><ActBifurcation /></div>

                <div className="h-screen w-full"><ActGenesis /></div>
                <div className="h-screen w-full"><ActSteps /></div>
                <div className="h-screen w-full"><ActTerrain /></div>

                {/* Act VI: Login */}
                <ActLogin />
            </div>
        </div>
    );
}
