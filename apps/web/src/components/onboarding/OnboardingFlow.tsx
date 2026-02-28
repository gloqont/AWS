"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { TutorialCompletionQuestionnaire, UserProfile } from "@/components/TutorialCompletionQuestionnaire";
import { TaxProfileWizard, TaxProfile } from "@/components/TaxProfileWizard";

export default function OnboardingFlow() {
    const router = useRouter();
    const [step, setStep] = useState<"check" | "investment" | "tax" | "completed">("check");

    useEffect(() => {
        // Check if we've already shown the onboarding in this session
        const shownInSession = sessionStorage.getItem("gloqont_onboarding_shown");

        if (shownInSession) {
            setStep("completed");
        } else {
            // Force start the flow
            setStep("investment");
        }
    }, []);

    const [investmentProfile, setInvestmentProfile] = useState<UserProfile | null>(null);

    const handleInvestmentComplete = (profile: UserProfile) => {
        // Investment profile is saved to localStorage by the component itself
        setInvestmentProfile(profile);
        setStep("tax");
    };

    const handleTaxComplete = (profile: TaxProfile) => {
        // Tax profile is saved to localStorage by the component itself

        // Mark as shown for this session
        sessionStorage.setItem("gloqont_onboarding_shown", "true");

        // Clear any previous tutorial state to ensure it starts fresh
        localStorage.removeItem("hasCompletedTutorial_v2");
        sessionStorage.removeItem("tutorialShownThisSession");

        setStep("completed");

        // Redirect to portfolio optimizer with tutorial param to start the tutorial immediately
        // Small delay to allow the modal to close visually if needed, though we are unmounting
        setTimeout(() => {
            router.push("/dashboard/portfolio-optimizer?tutorial=portfolio");
        }, 100);
    };

    const handleSkipAll = () => {
        // Use default tax profile
        const defaultTax: TaxProfile = {
            taxCountry: "US",
            taxSubJurisdiction: null,
            taxAccountType: "taxable",
            taxIncomeTier: "medium",
            taxFilingStatus: "single",
            taxHoldingPeriod: "short_term"
        };
        localStorage.setItem("gloqont_tax_profile", JSON.stringify(defaultTax));

        // Use default investment profile
        const defaultInv: UserProfile = {
            country: "US",
            currency: "USD",
            experience: "intermediate",
            riskBudget: "MEDIUM",
            onboardingCompleted: true,
        };
        localStorage.setItem("gloqont_user_profile", JSON.stringify(defaultInv));

        sessionStorage.setItem("gloqont_onboarding_shown", "true");
        localStorage.setItem("hasCompletedTutorial_v2", "true");
        setStep("completed");

        setTimeout(() => {
            router.push("/dashboard/portfolio-optimizer");
        }, 100);
    };

    if (step === "check" || step === "completed") {
        return null;
    }

    return (
        <>
            <TutorialCompletionQuestionnaire
                isOpen={step === "investment"}
                onComplete={handleInvestmentComplete}
                onSkip={handleSkipAll}
            />

            <TaxProfileWizard
                isOpen={step === "tax"}
                initialCountry={investmentProfile?.country}
                onComplete={handleTaxComplete}
                onSkip={handleSkipAll}
                onClose={() => {
                    handleTaxComplete({} as TaxProfile);
                }}
            />
        </>
    );
}
