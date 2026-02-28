'use client';

import { useEffect, useState } from 'react';
import { useTutorial } from './TutorialContext';
import { useRouter } from 'next/navigation';

interface TutorialFlowManagerProps {
  children: React.ReactNode;
}

const TutorialFlowManager: React.FC<TutorialFlowManagerProps> = ({ children }) => {
  const router = useRouter();
  const {
    isTutorialActive,
    currentStep,
    steps,
    completeTutorial
  } = useTutorial();

  // No need to initialize sequence since we handle the flow directly

  // Track which tutorial is currently active to enable sequential flow
  const [activeTutorialName, setActiveTutorialName] = useState<string | null>(null);

  // Detect when a tutorial is completed and move to the next in sequence
  useEffect(() => {
    if (!isTutorialActive) return;

    // Set the active tutorial name when a new tutorial starts based on the first step's ID
    if (steps.length > 0 && currentStep === 0) {
      // Check if this is a page-specific tutorial
      if (steps[0]?.id === 'portfolio-name') {
        setActiveTutorialName('portfolio');
      } else if (steps[0]?.id === 'scenario-portfolio-summary') {
        setActiveTutorialName('scenario');
      } else if (steps[0]?.id === 'tax-country') {
        setActiveTutorialName('tax-advisor');
      } else if (steps[0]?.id === 'tax-decision-info') {
        setActiveTutorialName('tax-impact');
      }
    }

    // Check if the current tutorial is completed
    if (steps.length > 0 && currentStep >= steps.length) {
      // Check which tutorial was just completed and move to the next
      if (activeTutorialName === 'portfolio') {
        // Portfolio Optimizer completed, move to Scenario Simulation
        setActiveTutorialName('scenario');
        // Navigate to the scenario simulation page with tutorial flag
        setTimeout(() => {
          router.push('/dashboard/scenario-simulation?tutorial=scenario');
        }, 500); // Small delay to ensure smooth transition
      } else if (activeTutorialName === 'scenario') {
        // Scenario Simulation completed, move to Tax Advisor
        setActiveTutorialName('tax-advisor');
        // Navigate to the tax advisor page with tutorial flag
        setTimeout(() => {
          router.push('/dashboard/tax-advisor?tutorial=tax-advisor');
        }, 500); // Small delay to ensure smooth transition
      } else if (activeTutorialName === 'tax-advisor') {
        // Tax Advisor completed, move to Tax Impact
        setActiveTutorialName('tax-impact');
        // Navigate to the tax impact page with tutorial flag
        setTimeout(() => {
          router.push('/dashboard/tax-impact?tutorial=tax-impact');
        }, 500); // Small delay to ensure smooth transition
      } else if (activeTutorialName === 'tax-impact') {
        // Tax Impact completed, end the tutorial
        setActiveTutorialName(null);
        setTimeout(() => completeTutorial(), 100);
      } else {
        // Fallback: if we cannot identify sequence context, complete cleanly.
        setTimeout(() => completeTutorial(), 100);
      }
    }
  }, [isTutorialActive, currentStep, steps, completeTutorial, activeTutorialName, router]);

  return <>{children}</>;
};

export default TutorialFlowManager;
