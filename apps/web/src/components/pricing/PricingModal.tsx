import React from 'react';
import { PricingCard } from '@/components/pricing/PricingCard';
import { X } from 'lucide-react';

interface PricingModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export function PricingModal({ isOpen, onClose }: PricingModalProps) {
    if (!isOpen) return null;

    const tiers = [
        {
            name: 'Free',
            price: 0,
            description: 'Evaluate the platform capabilities before fully committing.',
            buttonText: 'Get started for free',
            href: '#',
            onClick: onClose,
            features: [
                { name: 'Basic Scenario Simulations (3/mo)', included: true },
                { name: 'Standard Tax Strategy Insights', included: true },
                { name: 'Delayed Market Data', included: true },
                { name: 'Standard Email Support', included: false },
                { name: 'Brokerage API Integrations', included: false },
                { name: 'Multi-jurisdiction Tax Planning', included: false },
                { name: 'Dedicated Account Manager', included: false },
            ],
        },
        {
            name: 'Plus',
            price: 9,
            description: 'Essential tools for individual investors and beginners.',
            buttonText: 'Upgrade to Plus',
            href: '#',
            features: [
                { name: 'Basic Scenario Simulations (10/mo)', included: true },
                { name: 'Standard Tax Strategy Insights', included: true },
                { name: 'End-of-day Market Data', included: true },
                { name: 'Standard Email Support', included: true },
                { name: 'Brokerage API Integrations', included: false },
                { name: 'Multi-jurisdiction Tax Planning', included: false },
                { name: 'Dedicated Account Manager', included: false },
            ],
        },
        {
            name: 'Pro',
            price: 49,
            description: 'Advanced analytics and real-time data for serious traders.',
            isPopular: true,
            buttonText: 'Upgrade to Pro',
            href: '#',
            features: [
                { name: 'Advanced Scenario Simulations (100/mo)', included: true },
                { name: 'Advanced Tax Strategy Insights', included: true },
                { name: 'Real-time Market Data', included: true },
                { name: 'Priority Email Support', included: true },
                { name: 'Brokerage API Integrations (Up to 3)', included: true },
                { name: 'Multi-jurisdiction Tax Planning', included: false },
                { name: 'Dedicated Account Manager', included: false },
            ],
        },
        {
            name: 'Max',
            price: 99,
            description: 'Enterprise-grade tools for professionals and institutions.',
            buttonText: 'Contact Sales',
            href: '#',
            features: [
                { name: 'Unlimited Scenario Simulations', included: true },
                { name: 'Expert Tax Strategy Insights', included: true },
                { name: 'Real-time Market Data', included: true },
                { name: '24/7 Priority Support', included: true },
                { name: 'Unlimited Brokerage API Integrations', included: true },
                { name: 'Multi-jurisdiction Tax Planning', included: true },
                { name: 'Dedicated Account Manager', included: true },
            ],
        },
    ];

    return (
        <div className="fixed inset-0 z-[9999] bg-black/80 backdrop-blur-sm overflow-y-auto">
            <div className="min-h-screen py-16 relative flex flex-col items-center justify-center">

                {/* Close Button */}
                <button
                    onClick={onClose}
                    className="absolute top-6 right-6 p-2 rounded-full bg-white/5 hover:bg-white/10 text-white/60 hover:text-white transition-colors z-50"
                >
                    <X className="w-6 h-6" />
                </button>

                {/* Background glowing effects */}
                <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-[rgb(212,168,83)]/5 rounded-full blur-[120px] pointer-events-none -translate-y-1/2"></div>
                <div className="absolute bottom-0 right-1/4 w-[600px] h-[600px] bg-[rgb(201,150,59)]/5 rounded-full blur-[150px] pointer-events-none translate-y-1/3"></div>

                <div className="container mx-auto px-4 relative z-10 max-w-[90rem]">
                    <div className="text-center max-w-3xl mx-auto mb-12 animate-fade-in-up">
                        <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-white mb-4">
                            Unlock Full Simulation Power
                        </h2>
                        <p className="text-base text-[rgb(139,142,148)] leading-relaxed">
                            Upgrade your plan to simulate advanced market scenarios, optimize taxes, and make data-driven decisions before executing trades.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 items-stretch animate-slide-up animation-delay-200">
                        {tiers.map((tier, index) => (
                            <PricingCard key={index} {...tier} />
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
