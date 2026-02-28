import React from 'react';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

export default function PrivacyPage() {
    return (
        <div className="min-h-screen pt-24 pb-16 relative overflow-hidden">
            <div className="container mx-auto px-4 max-w-4xl relative z-10">
                <Link href="/pricing" className="inline-flex items-center text-[rgb(139,142,148)] hover:text-white mb-8 transition-colors">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Pricing
                </Link>
                <h1 className="text-4xl font-extrabold text-white mb-8">Privacy Policy</h1>

                <div className="prose prose-invert prose-p:text-[rgb(139,142,148)] prose-headings:text-white max-w-none">
                    <p>Last updated: {new Date().toLocaleDateString()}</p>

                    <h2>1. Information We Collect</h2>
                    <p>
                        We collect information you provide directly to us when you create an account, subscribe to a pricing tier, or use our financial simulation tools. This may include your name, email address, payment information, and the financial data you input for simulations.
                    </p>

                    <h2>2. How We Use Your Information</h2>
                    <p>
                        We use the information we collect to operate, maintain, and provide the features and functionality of the Service. We also use your information to enforce our subscription tier limits and ensure the security of our platform.
                    </p>

                    <h2>3. Data Security & Isolation</h2>
                    <p>
                        We take the security of your financial data extremely seriously. Gloqont employs strict strict Row-Level Security (RLS) and architectural data isolation. Your data is tethered exclusively to your unique user ID and is inaccessible by any other customer. Our administrative staff's access to user data is governed by strict Role-Based Access Control (RBAC) and is limited only to what is necessary for support and maintenance on isolated, separate systems.
                    </p>

                    <h2>4. Cookies</h2>
                    <p>
                        We use cookies and similar tracking technologies to track the activity on our Service and hold certain information. You can instruct your browser to refuse all cookies or to indicate when a cookie is being sent.
                    </p>

                    <h2>5. Contact Us</h2>
                    <p>
                        If you have any questions about this Privacy Policy or our strict data isolation practices, please contact our support team.
                    </p>
                </div>
            </div>
        </div>
    );
}
