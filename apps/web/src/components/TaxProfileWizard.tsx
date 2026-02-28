"use client";

import { useState, useEffect } from "react";

// ── Country-specific data ──────────────────────────────────────────────

const JURISDICTIONS: Record<string, { label: string; code: string; flag: string; currency: string; states?: Record<string, string> }> = {
    "US": { label: "United States", code: "US", flag: "🇺🇸", currency: "USD", states: { "NONE": "No State Tax", "CA": "California", "NY": "New York", "NJ": "New Jersey", "MA": "Massachusetts", "IL": "Illinois", "PA": "Pennsylvania", "TX": "Texas (0%)", "FL": "Florida (0%)", "WA": "Washington" } },
    "IN": { label: "India", code: "IN", flag: "🇮🇳", currency: "INR" },
    "CA": { label: "Canada", code: "CA", flag: "🇨🇦", currency: "CAD", states: { "ON": "Ontario", "QC": "Quebec", "AB": "Alberta", "BC": "British Columbia", "MB": "Manitoba", "SK": "Saskatchewan" } },
    "DE": { label: "Germany", code: "DE", flag: "🇩🇪", currency: "EUR" },
    "FR": { label: "France", code: "FR", flag: "🇫🇷", currency: "EUR" },
    "GB": { label: "United Kingdom", code: "GB", flag: "🇬🇧", currency: "GBP" },
    "NL": { label: "Netherlands", code: "NL", flag: "🇳🇱", currency: "EUR" },
};

// Country-specific account types
const COUNTRY_ACCOUNT_TYPES: Record<string, Record<string, string>> = {
    "US": {
        taxable: "Taxable Brokerage Account",
        ira_roth: "Roth IRA (Tax-Free Growth)",
        ira_traditional: "Traditional IRA (Tax-Deferred)",
        "401k": "401(k) / 403(b)",
        hsa: "HSA (Health Savings Account)",
    },
    "IN": {
        taxable: "Taxable Demat Account",
        ppf: "PPF (Public Provident Fund — Tax-Free)",
        nps: "NPS (National Pension Scheme)",
        elss: "ELSS (Tax-Saving Mutual Fund)",
    },
    "CA": {
        taxable: "Taxable Brokerage Account",
        tfsa: "TFSA (Tax-Free Savings Account)",
        rrsp: "RRSP (Registered Retirement Savings Plan)",
        resp: "RESP (Registered Education Savings Plan)",
    },
    "DE": {
        taxable: "Taxable Brokerage Account (Depot)",
        riester: "Riester-Rente (Subsidised Pension)",
        rurup: "Rürup-Rente / Basisrente",
    },
    "FR": {
        taxable: "Compte-Titres (Taxable)",
        pea: "PEA (Plan d'Épargne en Actions — Tax-Advantaged)",
        assurance_vie: "Assurance Vie (Life Insurance Wrapper)",
    },
    "GB": {
        taxable: "Taxable General Investment Account",
        isa: "ISA (Individual Savings Account — Tax-Free)",
        sipp: "SIPP (Self-Invested Personal Pension)",
        lisa: "Lifetime ISA (LISA)",
    },
    "NL": {
        taxable: "Taxable Brokerage Account",
        pensioen: "Pensioenrekening (Pension Account)",
        lijfrente: "Lijfrente (Annuity — Tax-Deferred)",
    },
};

// Fallback
const DEFAULT_ACCOUNT_TYPES: Record<string, string> = {
    taxable: "Taxable Brokerage Account",
};

const CURRENCY_SYMBOLS: Record<string, string> = {
    USD: "$", INR: "₹", CAD: "C$", EUR: "€", GBP: "£",
};

function getIncomeTiers(countryCode: string): Record<string, string> {
    const data = JURISDICTIONS[countryCode] || JURISDICTIONS["US"];
    const s = CURRENCY_SYMBOLS[data.currency] || "$";

    let l = 50, m = 200, h = 500, unit = "k";

    switch (countryCode) {
        case "IN":
            l = 5; m = 15; h = 50; unit = "L"; // Lakhs
            break;
        case "GB":
            l = 30; m = 80; h = 150;
            break;
        case "DE":
        case "FR":
        case "NL":
            l = 40; m = 100; h = 200;
            break;
        case "CA":
            l = 60; m = 150; h = 300;
            break;
        case "US":
        default:
            l = 50; m = 200; h = 500;
            break;
    }

    return {
        low: `Low Income (<${s}${l}${unit})`,
        medium: `Medium Income (${s}${l}${unit} – ${s}${m}${unit})`,
        high: `High Income (${s}${m}${unit} – ${s}${h}${unit})`,
        very_high: `Very High / UHNW (>${s}${h}${unit})`,
    };
}

const INCOME_TIERS: Record<string, string> = getIncomeTiers("USD");

export interface TaxProfile {
    taxCountry: string;
    taxSubJurisdiction: string | null;
    taxAccountType: string;
    taxIncomeTier: string;
    taxFilingStatus: string;
    taxHoldingPeriod: string;
}

interface TaxProfileWizardProps {
    isOpen: boolean;
    initialCountry?: string; // New prop
    onComplete: (profile: TaxProfile) => void;
    onClose: () => void;
}

export { JURISDICTIONS, COUNTRY_ACCOUNT_TYPES, DEFAULT_ACCOUNT_TYPES, INCOME_TIERS, getIncomeTiers, CURRENCY_SYMBOLS };

export function TaxProfileWizard({ isOpen, initialCountry, onComplete, onClose }: TaxProfileWizardProps) {
    // If initialCountry is provided, start at step 2, otherwise step 1
    const [step, setStep] = useState(initialCountry ? 2 : 1);

    const [profile, setProfile] = useState<TaxProfile>({
        taxCountry: initialCountry || "US", // Use initialCountry if available
        taxSubJurisdiction: null,
        taxAccountType: "taxable",
        taxIncomeTier: "medium",
        taxFilingStatus: "single",
        taxHoldingPeriod: "short_term"
    });

    // Reset state if initialCountry changes or wizard re-opens
    // This handles the case where the user might restart the flow
    // Reset state if initialCountry changes or wizard re-opens
    // This handles the case where the user might restart the flow
    // FIXED: Use useEffect instead of useState which only runs once
    useEffect(() => {
        if (initialCountry) {
            setProfile(p => ({ ...p, taxCountry: initialCountry }));
            setStep(2);
        }
    }, [initialCountry, isOpen]);

    if (!isOpen) return null;

    const handleNext = () => {
        // When moving from step 1 to step 2, reset account type to 'taxable'
        // since the options change per country
        if (step === 1) {
            setProfile(p => ({ ...p, taxAccountType: "taxable" }));
        }
        setStep(step + 1);
    };
    const handleBack = () => setStep(step - 1);

    const handleFinish = () => {
        localStorage.setItem("gloqont_tax_profile", JSON.stringify(profile));
        onComplete(profile);
    };

    const accountTypes = COUNTRY_ACCOUNT_TYPES[profile.taxCountry] || DEFAULT_ACCOUNT_TYPES;

    return (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className="w-full max-w-2xl bg-[#0a0a0a] border border-white/10 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">

                {/* Header */}
                <div className="p-8 border-b border-white/5 bg-gradient-to-r from-emerald-900/10 to-transparent">
                    <h2 className="text-2xl font-bold text-white mb-2">Institutional Tax Setup</h2>
                    <p className="text-white/60 text-sm">
                        Configure your tax environment so our engine can simulate precise after-tax outcomes for every decision.
                    </p>
                    <div className="flex gap-2 mt-6">
                        {[1, 2, 3].map((s) => (
                            <div key={s} className={`h-1 flex-1 rounded-full transition-all ${s <= step ? 'bg-emerald-500' : 'bg-white/10'}`} />
                        ))}
                    </div>
                </div>

                {/* Content */}
                <div className="p-8 overflow-y-auto flex-1">

                    {/* Step 1: Country */}
                    {step === 1 && (
                        <div className="animate-in fade-in slide-in-from-right-4 duration-300">
                            <h3 className="text-xl font-semibold text-white mb-2">Welcome! Select your Country</h3>
                            <p className="text-white/50 text-sm mb-6">We'll show the right tax accounts, rates, and rules for your jurisdiction.</p>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                {Object.entries(JURISDICTIONS).map(([code, data]) => (
                                    <button
                                        key={code}
                                        onClick={() => setProfile({ ...profile, taxCountry: code, taxSubJurisdiction: null, taxAccountType: "taxable" })}
                                        className={`flex items-center gap-4 p-4 rounded-xl border text-left transition-all ${profile.taxCountry === code
                                            ? 'bg-emerald-500/10 border-emerald-500/50 text-white shadow-[0_0_15px_rgba(16,185,129,0.2)]'
                                            : 'bg-white/5 border-white/5 text-white/60 hover:bg-white/10 hover:text-white'
                                            }`}
                                    >
                                        <span className="font-medium">{data.label}</span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Step 2: Details (country-specific) */}
                    {step === 2 && (
                        <div className="animate-in fade-in slide-in-from-right-4 duration-300">
                            <h3 className="text-xl font-semibold text-white mb-6">
                                Refine your {JURISDICTIONS[profile.taxCountry]?.label} tax profile
                            </h3>
                            <div className="space-y-6">

                                {/* State/Province (Conditional) */}
                                {JURISDICTIONS[profile.taxCountry]?.states && (
                                    <div>
                                        <label className="block text-sm text-white/50 mb-2">State / Province</label>
                                        <div className="grid grid-cols-2 gap-2">
                                            {Object.entries(JURISDICTIONS[profile.taxCountry].states!).map(([code, name]) => (
                                                <button
                                                    key={code}
                                                    onClick={() => setProfile({ ...profile, taxSubJurisdiction: code })}
                                                    className={`px-3 py-2 rounded-lg text-sm border transition-all text-left truncate ${profile.taxSubJurisdiction === code
                                                        ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300'
                                                        : 'bg-white/5 border-white/5 text-white/60 hover:bg-white/10'
                                                        }`}
                                                >
                                                    {name}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Account Type (Country-Specific) */}
                                <div>
                                    <label className="block text-sm text-white/50 mb-2">Account Type</label>
                                    <div className="space-y-2">
                                        {Object.entries(accountTypes).map(([v, l]) => (
                                            <button
                                                key={v}
                                                onClick={() => setProfile({ ...profile, taxAccountType: v })}
                                                className={`w-full px-4 py-3 rounded-xl border text-left text-sm transition-all ${profile.taxAccountType === v
                                                    ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300'
                                                    : 'bg-white/5 border-white/5 text-white/60 hover:bg-white/10 hover:text-white'
                                                    }`}
                                            >
                                                {l}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm text-white/50 mb-2">Approx. Income</label>
                                        <select
                                            className="w-full bg-white/5 border border-white/10 p-3 rounded-xl text-white outline-none focus:border-emerald-500/50"
                                            value={profile.taxIncomeTier}
                                            onChange={(e) => setProfile({ ...profile, taxIncomeTier: e.target.value })}
                                        >
                                            {Object.entries(getIncomeTiers(profile.taxCountry)).map(([v, l]) => (
                                                <option key={v} value={v} className="bg-gray-900">{l}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-sm text-white/50 mb-2">Filing Status</label>
                                        <select
                                            className="w-full bg-white/5 border border-white/10 p-3 rounded-xl text-white outline-none focus:border-emerald-500/50"
                                            value={profile.taxFilingStatus}
                                            onChange={(e) => setProfile({ ...profile, taxFilingStatus: e.target.value })}
                                        >
                                            <option value="single" className="bg-gray-900">Single</option>
                                            <option value="married_joint" className="bg-gray-900">Married (Joint)</option>
                                        </select>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Step 3: Confirmation */}
                    {step === 3 && (
                        <div className="animate-in fade-in slide-in-from-right-4 duration-300 text-center">
                            <div className="w-16 h-16 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                                <span className="text-emerald-500 text-3xl">✓</span>
                            </div>
                            <h3 className="text-2xl font-bold text-white mb-2">You're All Set!</h3>
                            <p className="text-white/60 mb-8">
                                The GLOQONT Tax Engine is now calibrated for
                                <span className="text-white font-medium"> {JURISDICTIONS[profile.taxCountry]?.label}</span>
                                {profile.taxSubJurisdiction && <span> ({profile.taxSubJurisdiction})</span>}.
                                Simulations will automatically apply the correct capital gains rules, slab rates, and exemptions.
                            </p>

                            <div className="bg-white/5 rounded-xl p-4 text-left border border-white/10 mb-8 max-w-sm mx-auto">
                                <div className="text-xs text-white/40 uppercase tracking-wider mb-3">Configuration Summary</div>
                                <div className="flex justify-between text-sm mb-2">
                                    <span className="text-white/60">Country</span>
                                    <span className="text-white">{JURISDICTIONS[profile.taxCountry]?.label}</span>
                                </div>
                                {profile.taxSubJurisdiction && (
                                    <div className="flex justify-between text-sm mb-2">
                                        <span className="text-white/60">State</span>
                                        <span className="text-white">{profile.taxSubJurisdiction}</span>
                                    </div>
                                )}
                                <div className="flex justify-between text-sm mb-2">
                                    <span className="text-white/60">Account</span>
                                    <span className="text-white">{accountTypes[profile.taxAccountType] || profile.taxAccountType}</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-white/60">Income</span>
                                    <span className="text-white">{getIncomeTiers(profile.taxCountry)[profile.taxIncomeTier] || profile.taxIncomeTier}</span>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-6 border-t border-white/5 flex justify-between bg-black/20">
                    {step > 1 ? (
                        <button
                            onClick={handleBack}
                            className="px-6 py-3 rounded-xl text-white/60 hover:text-white hover:bg-white/5 transition"
                        >
                            Back
                        </button>
                    ) : (
                        <div /> // Spacer
                    )}

                    {step < 3 ? (
                        <button
                            onClick={handleNext}
                            className="px-8 py-3 rounded-xl bg-white text-black font-semibold hover:bg-emerald-400 hover:text-black transition shadow-lg shadow-emerald-500/10"
                        >
                            Next
                        </button>
                    ) : (
                        <button
                            onClick={handleFinish}
                            className="px-8 py-3 rounded-xl bg-emerald-500 text-black font-bold hover:bg-emerald-400 transition shadow-lg shadow-emerald-500/20"
                        >
                            Finish Setup
                        </button>
                    )}
                </div>

            </div>
        </div>
    );
}
