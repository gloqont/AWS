'use client';

import React, { createContext, useContext, useState, ReactNode, useEffect } from 'react';

export interface TutorialStep {
  id: string;
  title: string;
  description: string;
  elementId: string;
  position?: 'top' | 'bottom' | 'left' | 'right' | 'center';
}

interface TutorialContextType {
  isTutorialActive: boolean;
  currentStep: number;
  steps: TutorialStep[];
  startTutorial: (steps: TutorialStep[]) => void;
  nextStep: () => void;
  prevStep: () => void;
  endTutorial: () => void;
  completeTutorial: () => void;
  goToStep: (stepIndex: number) => void;
  setCurrentStep: (step: number) => void;
}

const TutorialContext = createContext<TutorialContextType | undefined>(undefined);

export const useTutorial = () => {
  const context = useContext(TutorialContext);
  if (!context) {
    throw new Error('useTutorial must be used within a TutorialProvider');
  }
  return context;
};

interface TutorialProviderProps {
  children: ReactNode;
}

export const TutorialProvider: React.FC<TutorialProviderProps> = ({ children }) => {
  const [isTutorialActive, setIsTutorialActive] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [steps, setSteps] = useState<TutorialStep[]>([]);

  // Check if user has completed the first-time tutorial
  useEffect(() => {
    const hasCompletedTutorial = localStorage.getItem('hasCompletedTutorial_v2');
    if (!hasCompletedTutorial) {
      // Optionally start the first-time tutorial here
    }
  }, []);

  const startTutorial = (tutorialSteps: TutorialStep[]) => {
    setSteps(tutorialSteps);
    setCurrentStep(0);
    setIsTutorialActive(true);
  };

  const nextStep = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(prev => prev + 1);
    } else {
      // Instead of ending the tutorial, we should allow TutorialFlowManager to handle navigation
      // So we increment currentStep beyond the length to signal completion
      setCurrentStep(prev => prev + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1);
    }
  };

  const goToStep = (stepIndex: number) => {
    if (stepIndex >= 0 && stepIndex < steps.length) {
      setCurrentStep(stepIndex);
    }
  };

  const endTutorial = () => {
    setIsTutorialActive(false);
    setCurrentStep(0);
    setSteps([]);
  };

  const completeTutorial = () => {
    endTutorial();
    localStorage.setItem('hasCompletedTutorial_v2', 'true');
  };

  return (
    <TutorialContext.Provider
      value={{
        isTutorialActive,
        currentStep,
        steps,
        startTutorial,
        nextStep,
        prevStep,
        endTutorial,
        completeTutorial,
        goToStep,
        setCurrentStep: (step: number) => setCurrentStep(step),
      }}
    >
      {children}
    </TutorialContext.Provider>
  );
};
