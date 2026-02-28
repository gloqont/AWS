import React from 'react';
import { PricingCard } from '@/components/pricing/PricingCard';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

export default function PricingPage() {
    const tiers = [
        {
            name: 'Free',
            price: 0,
            description: 'Evaluate the platform capabilities before fully committing.',
            buttonText: 'Current Plan',
            href: '/dashboard',
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
            href: '/login', // Redirects to login/signup for now
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
            href: '/login',
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
            href: '/login',
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
        <div className="min-h-screen pt-24 pb-16 relative overflow-hidden flex flex-col items-center justify-center">
            {/* Background glowing effects */}
            <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-[rgb(212,168,83)]/5 rounded-full blur-[120px] pointer-events-none -translate-y-1/2"></div>
            <div className="absolute bottom-0 right-1/4 w-[600px] h-[600px] bg-[rgb(201,150,59)]/5 rounded-full blur-[150px] pointer-events-none translate-y-1/3"></div>

            <div className="container mx-auto px-4 relative z-10 max-w-7xl">
                <Link href="/" className="inline-flex items-center text-[rgb(139,142,148)] hover:text-white mb-8 transition-colors">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Home
                </Link>
                <div className="text-center max-w-3xl mx-auto mb-16 animate-fade-in-up">
                    <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-white mb-6">
                        Predict the Future <br className="hidden md:block" />
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-[rgb(212,168,83)] to-[rgb(201,150,59)] animate-gradient-text">
                            Optimize Your Present
                        </span>
                    </h1>
                    <p className="text-lg text-[rgb(139,142,148)] leading-relaxed">
                        Choose the perfect plan to simulate market scenarios, optimize your taxes, and make data-driven trade decisions before executing them.
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-stretch pt-4 animate-slide-up animation-delay-200 lg:px-12">
                    {tiers.map((tier, index) => (
                        <PricingCard key={index} {...tier} />
                    ))}
                </div>

                <div className="mt-20 text-center flex flex-col sm:flex-row items-center justify-center gap-6 text-sm text-[rgb(139,142,148)]">
                    <Link href="/terms" className="hover:text-white transition-colors underline underline-offset-4 decoration-white/20 hover:decoration-white/50">Terms of Service</Link>
                    <span className="hidden sm:inline w-1 h-1 rounded-full bg-white/20"></span>
                    <Link href="/privacy" className="hover:text-white transition-colors underline underline-offset-4 decoration-white/20 hover:decoration-white/50">Privacy Policy</Link>
                </div>
            </div>
        </div>
    );
}
