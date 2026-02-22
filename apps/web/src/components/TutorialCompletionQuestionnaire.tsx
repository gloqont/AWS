"use client";

import { useState, useEffect } from "react";
import { JURISDICTIONS } from "./TaxProfileWizard"; // Reuse or redefine if needed

// Additional metadata for the questionnaire
const EXPERIENCE_LEVELS = [
    { id: "beginner", label: "Beginner", description: "New to trading and investing." },
    { id: "intermediate", label: "Intermediate", description: "Some experience with stocks and basic strategies." },
    { id: "advanced", label: "Advanced", description: "Experienced with complex instruments and strategies." },
    { id: "pro", label: "Professional", description: "Trade for a living or manage significant capital." },
];

const RISK_BUDGETS = [
    { id: "LOW", label: "Conservative (Low Risk)", description: "Prioritize capital preservation." },
    { id: "MEDIUM", label: "Balanced (Medium Risk)", description: "Balance between growth and safety." },
    { id: "HIGH", label: "Aggressive (High Risk)", description: "Maximize returns, willing to accept higher volatility." },
];

export interface UserProfile {
    country: string;
    currency: string;
    experience: string;
    riskBudget: string;
    onboardingCompleted: boolean;
}

interface QuestionnaireProps {
    isOpen: boolean;
    onComplete: (profile: UserProfile) => void;
    initialProfile?: Partial<UserProfile>;
}

export function TutorialCompletionQuestionnaire({ isOpen, onComplete, initialProfile }: QuestionnaireProps) {
    const [step, setStep] = useState(1);
    const [profile, setProfile] = useState<UserProfile>({
        country: initialProfile?.country || "US",
        currency: "USD", // Default, will update based on country
        experience: initialProfile?.experience || "intermediate",
        riskBudget: initialProfile?.riskBudget || "MEDIUM",
        onboardingCompleted: true,
    });

    // Update currency when country changes
    useEffect(() => {
        switch (profile.country) {
            case "IN": setProfile(p => ({ ...p, currency: "INR" })); break;
            case "GB": setProfile(p => ({ ...p, currency: "GBP" })); break;
            case "EU": // General Eurozone
            case "DE":
            case "FR":
            case "NL":
                setProfile(p => ({ ...p, currency: "EUR" })); break;
            case "CA": setProfile(p => ({ ...p, currency: "CAD" })); break;
            default: setProfile(p => ({ ...p, currency: "USD" })); break;
        }
    }, [profile.country]);

    if (!isOpen) return null;

    const handleNext = () => setStep(step + 1);
    const handleBack = () => setStep(step - 1);

    const handleFinish = () => {
        // Save to localStorage
        localStorage.setItem("gloqont_user_profile", JSON.stringify(profile));
        // Also update legacy tax profile for compatibility if needed
        const legacyTaxProfile = {
            taxCountry: profile.country,
            taxSubJurisdiction: null,
            taxAccountType: "taxable", // Default
            taxIncomeTier: "medium", // Default
            taxFilingStatus: "single", // Default
            taxHoldingPeriod: "short_term" // Default
        };
        localStorage.setItem("gloqont_tax_profile", JSON.stringify(legacyTaxProfile));

        onComplete(profile);
    };

    return (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className="w-full max-w-2xl bg-[#0a0a0a] border border-white/10 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">

                {/* Header */}
                <div className="p-8 border-b border-white/5 bg-gradient-to-r from-blue-900/10 to-transparent">
                    <h2 className="text-2xl font-bold text-white mb-2">🚀 Profile Setup</h2>
                    <p className="text-white/60 text-sm">
                        Let's customize GLOQONT for your region and investment style.
                    </p>
                    <div className="flex gap-2 mt-6">
                        {[1, 2, 3].map((s) => (
                            <div key={s} className={`h-1 flex-1 rounded-full transition-all ${s <= step ? 'bg-blue-500' : 'bg-white/10'}`} />
                        ))}
                    </div>
                </div>

                {/* Content */}
                <div className="p-8 overflow-y-auto flex-1">

                    {/* Step 1: Country */}
                    {step === 1 && (
                        <div className="animate-in fade-in slide-in-from-right-4 duration-300">
                            <h3 className="text-xl font-semibold text-white mb-2">Where are you based?</h3>
                            <p className="text-white/50 text-sm mb-6">We'll adapt currency, market hours, and tax rules.</p>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                {Object.entries(JURISDICTIONS).map(([code, data]) => (
                                    <button
                                        key={code}
                                        onClick={() => setProfile({ ...profile, country: code })}
                                        className={`flex items-center gap-4 p-4 rounded-xl border text-left transition-all ${profile.country === code
                                            ? 'bg-blue-500/10 border-blue-500/50 text-white shadow-[0_0_15px_rgba(59,130,246,0.2)]'
                                            : 'bg-white/5 border-white/5 text-white/60 hover:bg-white/10 hover:text-white'
                                            }`}
                                    >
                                        <span className="text-3xl filter drop-shadow-lg">{data.flag}</span>
                                        <span className="font-medium">{data.label}</span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Step 2: Experience */}
                    {step === 2 && (
                        <div className="animate-in fade-in slide-in-from-right-4 duration-300">
                            <h3 className="text-xl font-semibold text-white mb-2">What is your trading experience?</h3>
                            <p className="text-white/50 text-sm mb-6">Helps us tailor complexity and warnings.</p>
                            <div className="space-y-3">
                                {EXPERIENCE_LEVELS.map((level) => (
                                    <button
                                        key={level.id}
                                        onClick={() => setProfile({ ...profile, experience: level.id })}
                                        className={`w-full p-4 rounded-xl border text-left transition-all ${profile.experience === level.id
                                            ? 'bg-blue-500/10 border-blue-500/50 text-white'
                                            : 'bg-white/5 border-white/5 text-white/60 hover:bg-white/10 hover:text-white'
                                            }`}
                                    >
                                        <div className="font-medium text-lg">{level.label}</div>
                                        <div className="text-sm text-white/40">{level.description}</div>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Step 3: Risk Budget */}
                    {step === 3 && (
                        <div className="animate-in fade-in slide-in-from-right-4 duration-300">
                            <h3 className="text-xl font-semibold text-white mb-2">What is your risk appetite?</h3>
                            <p className="text-white/50 text-sm mb-6">Sets default constraints for portfolio optimization.</p>
                            <div className="space-y-3">
                                {RISK_BUDGETS.map((rb) => (
                                    <button
                                        key={rb.id}
                                        onClick={() => setProfile({ ...profile, riskBudget: rb.id })}
                                        className={`w-full p-4 rounded-xl border text-left transition-all ${profile.riskBudget === rb.id
                                            ? 'bg-blue-500/10 border-blue-500/50 text-white'
                                            : 'bg-white/5 border-white/5 text-white/60 hover:bg-white/10 hover:text-white'
                                            }`}
                                    >
                                        <div className="font-medium text-lg">{rb.label}</div>
                                        <div className="text-sm text-white/40">{rb.description}</div>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-6 border-t border-white/5 flex justify-between bg-black/20">
                    {step > 1 ? (
                        <button onClick={handleBack} className="px-6 py-3 rounded-xl text-white/60 hover:text-white hover:bg-white/5 transition">Back</button>
                    ) : <div />}

                    {step < 3 ? (
                        <button onClick={handleNext} className="px-8 py-3 rounded-xl bg-white text-black font-semibold hover:bg-blue-400 hover:text-black transition shadow-lg">Next</button>
                    ) : (
                        <button onClick={handleFinish} className="px-8 py-3 rounded-xl bg-blue-500 text-white font-bold hover:bg-blue-400 transition shadow-lg shadow-blue-500/20">Finish Setup</button>
                    )}
                </div>
            </div>
        </div>
    );
}
