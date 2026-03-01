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

    if (step === "check" || step === "completed") {
        return null;
    }

    return (
        <>
            <TutorialCompletionQuestionnaire
                isOpen={step === "investment"}
                onComplete={handleInvestmentComplete}
            // No create/close handlers needed as we control the flow
            />

            <TaxProfileWizard
                isOpen={step === "tax"}
                initialCountry={investmentProfile?.country}
                onComplete={handleTaxComplete}
                onClose={() => {
                    // If they try to close it, we should probably just keep it open or treated as complete?
                    // The requirement is "make them in one like everytime i log in... should immediately be present"
                    // So we probably shouldn't allow closing without completion, OR closing skips to tutorial.
                    // Let's treat close as 'skip remaining' but still trigger tutorial? 
                    // Better to enforce completion as per "no matter so now both of these would come"
                    // But for safety, if they forcibly close, let's move to next step.
                    handleTaxComplete({} as TaxProfile);
                }}
            />
        </>
    );
}
