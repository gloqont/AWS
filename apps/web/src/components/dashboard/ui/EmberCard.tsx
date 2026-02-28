import React from "react";

interface EmberCardProps {
    children: React.ReactNode;
    className?: string;
    title?: string;
    subtitle?: string;
    id?: string;
}

export function EmberCard({ children, className = "", title, subtitle, id }: EmberCardProps) {
    return (
        <div id={id} className={`relative group ${className}`}>
            {/* Dynamic Glow Border Effect */}
            <div className="absolute -inset-0.5 bg-gradient-to-b from-[#D4A853]/20 to-transparent rounded-2xl blur opacity-0 group-hover:opacity-100 transition duration-500" />

            {/* Main Card Content */}
            <div className="relative h-full bg-[#0a0a0a]/80 backdrop-blur-xl border border-[#D4A853]/20 rounded-2xl p-6 shadow-xl transition-all hover:border-[#D4A853]/40">

                {/* Decorative Corners */}
                <div className="absolute top-0 left-0 w-3 h-3 border-t border-l border-[#D4A853]/30 rounded-tl-lg -mt-px -ml-px" />
                <div className="absolute top-0 right-0 w-3 h-3 border-t border-r border-[#D4A853]/30 rounded-tr-lg -mt-px -mr-px" />
                <div className="absolute bottom-0 left-0 w-3 h-3 border-b border-l border-[#D4A853]/30 rounded-bl-lg -mb-px -ml-px" />
                <div className="absolute bottom-0 right-0 w-3 h-3 border-b border-r border-[#D4A853]/30 rounded-br-lg -mb-px -mr-px" />

                {/* Header */}
                {(title || subtitle) && (
                    <div className="mb-6 border-b border-white/5 pb-4">
                        {title && (
                            <h3 className="text-xl font-bold text-white tracking-wide uppercase flex items-center gap-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-[#D4A853] shadow-[0_0_10px_#D4A853]" />
                                {title}
                            </h3>
                        )}
                        {subtitle && (
                            <p className="text-[#D4A853]/60 text-xs font-mono mt-1 pl-4 uppercase tracking-wider">
                                {subtitle}
                            </p>
                        )}
                    </div>
                )}

                {children}
            </div>
        </div>
    );
}
