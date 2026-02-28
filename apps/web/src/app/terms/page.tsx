import React from 'react';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

export default function TermsPage() {
    return (
        <div className="min-h-screen pt-24 pb-16 relative overflow-hidden">
            <div className="container mx-auto px-4 max-w-4xl relative z-10">
                <Link href="/pricing" className="inline-flex items-center text-[rgb(139,142,148)] hover:text-white mb-8 transition-colors">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Pricing
                </Link>
                <h1 className="text-4xl font-extrabold text-white mb-8">Terms of Service</h1>

                <div className="prose prose-invert prose-p:text-[rgb(139,142,148)] prose-headings:text-white max-w-none">
                    <p>Last updated: {new Date().toLocaleDateString()}</p>

                    <h2>1. Agreement to Terms</h2>
                    <p>
                        By accessing or using Gloqont, you agree to be bound by these Terms of Service and all applicable laws and regulations. If you do not agree with any of these terms, you are prohibited from using or accessing this site.
                    </p>

                    <h2>2. Use License</h2>
                    <p>
                        Permission is granted to temporarily download one copy of the materials (information or software) on Gloqont's website for personal, non-commercial transitory viewing only. This is the grant of a license, not a transfer of title.
                    </p>

                    <h2>3. Subscriptions and Feature Limits</h2>
                    <p>
                        Gloqont offers various subscription tiers (Plus, Pro, Max). By subscribing, you agree to pay the fees associated with your chosen tier. Feature limits (e.g., number of scenario simulations, API access) are strictly enforced based on your active subscription tier.
                    </p>

                    <h2>4. Data and Privacy</h2>
                    <p>
                        Your use of Gloqont is also governed by our Privacy Policy. We implement strict data isolation protocols to ensure your financial scenarios and data remain completely separate and secure from other users.
                    </p>

                    <h2>5. Disclaimer</h2>
                    <p>
                        The materials on Gloqont's website are provided on an 'as is' basis. Gloqont is a simulation and analytical tool. The predictions and optimizations provided are for informational purposes only and do not constitute financial advice. Gloqont makes no warranties, expressed or implied, and hereby disclaims and negates all other warranties including, without limitation, implied warranties or conditions of merchantability, fitness for a particular purpose, or non-infringement of intellectual property or other violation of rights.
                    </p>
                </div>
            </div>
        </div>
    );
}
