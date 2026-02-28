import React from 'react';
import Link from 'next/link';
import { Check } from 'lucide-react';

interface PricingFeature {
    name: string;
    included: boolean;
}

interface PricingTierProps {
    name: string;
    price: number;
    description: string;
    features: PricingFeature[];
    isPopular?: boolean;
    buttonText: string;
    href: string;
    onClick?: () => void;
}

export function PricingCard({
    name,
    price,
    description,
    features,
    isPopular = false,
    buttonText,
    href,
    onClick,
}: PricingTierProps) {
    return (
        <div
            className={`relative rounded-2xl p-8 border backdrop-blur-sm card-hover flex flex-col h-full ${isPopular
                ? 'border-[rgb(201,150,59)]/50 bg-[rgb(10,10,12)]/80 shadow-[0_0_30px_rgba(201,150,59,0.1)]'
                : 'border-white/5 bg-black/40'
                }`}
        >
            {isPopular && (
                <div className="absolute top-0 right-8 transform -translate-y-1/2">
                    <div className="bg-gradient-to-r from-[rgb(212,168,83)] to-[rgb(201,150,59)] text-black text-xs font-bold uppercase tracking-wider py-1 px-3 rounded-full animate-breathe">
                        Most Popular
                    </div>
                </div>
            )}

            <div className="mb-8">
                <h3 className="text-xl font-bold text-white mb-2">{name}</h3>
                <p className="text-sm text-[rgb(139,142,148)] min-h-[40px]">{description}</p>
            </div>

            <div className="mb-8">
                <div className="flex items-baseline text-white">
                    <span className="text-4xl font-extrabold tracking-tight">${price}</span>
                    <span className="ml-1 text-xl font-medium text-[rgb(139,142,148)]">/month</span>
                </div>
            </div>

            <ul className="flex-1 space-y-4 mb-8">
                {features.map((feature, index) => (
                    <li key={index} className="flex items-start">
                        <div className={`flex-shrink-0 w-5 h-5 flex items-center justify-center rounded-full mt-0.5 ${feature.included ? 'bg-[rgb(201,150,59)]/20 text-[rgb(212,168,83)]' : 'bg-white/5 text-[rgb(139,142,148)]/50'}`}>
                            <Check className="w-3 h-3" />
                        </div>
                        <span className={`ml-3 text-sm ${feature.included ? 'text-white/90' : 'text-[rgb(139,142,148)] line-through'}`}>
                            {feature.name}
                        </span>
                    </li>
                ))}
            </ul>

            {onClick ? (
                <button
                    onClick={onClick}
                    className={`w-full py-3 px-6 rounded-lg font-medium text-center transition-all duration-300 btn-magnetic ${isPopular
                        ? 'bg-gradient-to-r from-[rgb(212,168,83)] to-[rgb(201,150,59)] text-black hover:shadow-[0_0_20px_rgba(212,168,83,0.3)]'
                        : 'bg-white/5 text-white hover:bg-white/10 border border-white/10'
                        }`}
                >
                    {buttonText}
                </button>
            ) : (
                <Link
                    href={href}
                    className={`w-full py-3 px-6 rounded-lg font-medium text-center transition-all duration-300 btn-magnetic ${isPopular
                        ? 'bg-gradient-to-r from-[rgb(212,168,83)] to-[rgb(201,150,59)] text-black hover:shadow-[0_0_20px_rgba(212,168,83,0.3)]'
                        : 'bg-white/5 text-white hover:bg-white/10 border border-white/10'
                        }`}
                >
                    {buttonText}
                </Link>
            )}
        </div>
    );
}
