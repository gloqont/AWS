'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useTutorial } from './TutorialContext';
import { useRouter, usePathname } from 'next/navigation';
import {
  FIRST_TIME_TUTORIAL_STEPS,
  PORTFOLIO_OPTIMIZER_TUTORIAL,
  TAX_ADVISOR_TUTORIAL,
  SCENARIO_SIMULATION_TUTORIAL,
  TAX_IMPACT_TUTORIAL
} from './tutorialContent';

interface TutorialOverlayProps {
  children: React.ReactNode;
}

const TutorialOverlay: React.FC<TutorialOverlayProps> = ({ children }) => {
  const { isTutorialActive, currentStep, steps, nextStep, prevStep, endTutorial, startTutorial } = useTutorial();
  const router = useRouter();
  const pathname = usePathname();
  const overlayRef = useRef<HTMLDivElement>(null);
  const [currentPage, setCurrentPage] = useState('');

  // Determine current page from pathname
  useEffect(() => {
    if (pathname.includes('/portfolio-optimizer')) {
      setCurrentPage('portfolio-optimizer');
    } else if (pathname.includes('/scenario-simulation')) {
      setCurrentPage('scenario-simulation');
    } else if (pathname.includes('/tax-advisor')) {
      setCurrentPage('tax-advisor');
    } else if (pathname.includes('/tax-impact')) {
      setCurrentPage('tax-impact');
    } else {
      setCurrentPage('');
    }
  }, [pathname]);

  // Calculate the position and dimensions of the highlighted element
  useEffect(() => {
    if (!isTutorialActive || steps.length === 0) return;

    const currentStepData = steps[currentStep];
    const element = document.getElementById(currentStepData.elementId);

    if (element && overlayRef.current) {
      const rect = element.getBoundingClientRect();
      const overlay = overlayRef.current;

      // Position the highlight box around the target element
      overlay.style.position = 'fixed';
      overlay.style.left = `${rect.left - 5}px`; // Add padding
      overlay.style.top = `${rect.top - 5}px`;
      overlay.style.width = `${rect.width + 10}px`;
      overlay.style.height = `${rect.height + 10}px`;
      overlay.style.zIndex = '9998';
      overlay.style.pointerEvents = 'none';

      // Add a slight margin to make the highlight more visible
      overlay.style.boxShadow = '0 0 0 9999px rgba(0, 0, 0, 0.7)';
      overlay.style.borderRadius = '12px';
      overlay.style.transform = 'scale(1.05)'; // Zoom effect
      overlay.style.transition = 'all 0.3s ease';
    }
  }, [isTutorialActive, currentStep, steps]);

  // State to hold the current step data and rect for consistent hook usage
  const [tutorialState, setTutorialState] = useState<{currentStepData: any, element: HTMLElement | null, rect: DOMRect | null} | null>(null);

  // Update tutorial state when tutorial is active
  useEffect(() => {
    if (isTutorialActive && steps.length > 0) {
      const currentStepData = steps[currentStep];
      const element = document.getElementById(currentStepData.elementId);
      const rect = element?.getBoundingClientRect() || null;
      setTutorialState({ currentStepData, element, rect });
    } else {
      setTutorialState(null);
    }
  }, [isTutorialActive, steps, currentStep, steps.length]);

  
  
  // Position the tooltip after it renders
  useEffect(() => {
    if (!isTutorialActive || !tutorialState?.rect) return;

    const tooltip = document.getElementById('tutorial-tooltip');
    if (!tooltip) return;

    // Wait for the next tick to ensure the element is rendered
    setTimeout(() => {
      const rect = tutorialState.rect!;
      // Calculate position to keep tooltip within viewport and avoid overlapping the highlighted element

      // Default position: to the right of the element
      let leftPos = rect.left + rect.width + 20;
      let topPos = rect.top;

      // Check if tooltip would go off screen to the right
      if (leftPos + tooltip.offsetWidth > window.innerWidth) {
        // Position to the left of the element
        leftPos = rect.left - tooltip.offsetWidth - 20;

        // If that would go off the left side, position it below the element
        if (leftPos < 0) {
          leftPos = rect.left;
          topPos = rect.top + rect.height + 20;

          // If that would go off the bottom, position it above the element
          if (topPos + tooltip.offsetHeight > window.innerHeight) {
            topPos = rect.top - tooltip.offsetHeight - 20;
            // If that would go off the top, center it vertically
            if (topPos < 0) {
              topPos = rect.top + rect.height / 2 - tooltip.offsetHeight / 2;
            }
          }
        }
      }
      // Check if tooltip would go off screen at the bottom when positioned to the right
      else if (topPos + tooltip.offsetHeight > window.innerHeight) {
        // Position it below the element
        topPos = rect.top + rect.height + 20;

        // If that would go off the bottom, position it above the element
        if (topPos + tooltip.offsetHeight > window.innerHeight) {
          topPos = rect.top - tooltip.offsetHeight - 20;

          // If that would go off the top, center it vertically
          if (topPos < 0) {
            topPos = rect.top + rect.height / 2 - tooltip.offsetHeight / 2;
          }
        }
      }

      // Apply the calculated position
      tooltip.style.left = `${leftPos}px`;
      tooltip.style.top = `${topPos}px`;
      tooltip.style.transform = 'none'; // Override the default centering
    }, 100); // Increased delay to ensure animation completes
  }, [isTutorialActive, tutorialState]);

  if (!isTutorialActive) {
    return <>{children}</>;
  }

  // Render the tutorial overlay when active
  return (
    <>
      {children}
      {/* Overlay to dim the rest of the screen */}
      <div
        className="fixed inset-0 bg-black/70 z-50 pointer-events-auto"
        style={{ zIndex: 9997 }}
        onClick={endTutorial}
      />

      {/* Highlight box around the target element with zoom effect */}
      <div
        ref={overlayRef}
        className="fixed border-4 border-yellow-400 rounded-xl z-50 animate-pulse shadow-lg shadow-yellow-400/50"
        style={{
          boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.5)',
          borderRadius: '12px',
          transition: 'all 0.3s ease',
          transform: 'scale(1.05)', // Slight zoom effect
          zIndex: 9998
        }}
      />

      {/* Tooltip with tutorial content - positioned to stay within viewport and avoid overlapping the highlighted element */}
      <div
        id="tutorial-tooltip"
        className="fixed bg-gradient-to-br from-white to-gray-50 text-gray-900 p-6 rounded-2xl shadow-2xl z-50 max-w-xs sm:max-w-sm md:max-w-md pointer-events-auto border-2 border-blue-400 shadow-blue-500/30"
        style={{
          left: '50%',
          top: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 9999,
          maxWidth: '90vw', // Ensure it fits on small screens
          maxHeight: '80vh',
          overflowY: 'auto',
          backdropFilter: 'blur(10px)'
        }}
      >
        <div className="mb-4">
          <h3 className="text-xl font-bold text-blue-700 flex items-center gap-2">
            <span className="bg-blue-100 text-blue-700 rounded-full w-6 h-6 flex items-center justify-center text-sm">
              {currentStep + 1}
            </span>
            {tutorialState?.currentStepData.title}
          </h3>
        </div>
        <p className="text-gray-700 mb-5 text-base leading-relaxed">{tutorialState?.currentStepData.description}</p>

        <div className="flex flex-col sm:flex-row justify-between items-center gap-3 sm:gap-0 pt-3 border-t border-gray-200">
          <div className="text-sm text-gray-600 font-medium">
            Step {currentStep + 1} of {steps.length}
          </div>

          <div className="flex space-x-3">
            {currentStep > 0 && (
              <button
                onClick={prevStep}
                className="px-4 py-2 bg-gradient-to-r from-gray-200 to-gray-300 text-gray-800 rounded-lg hover:from-gray-300 hover:to-gray-400 transition-all text-sm font-medium shadow-sm"
              >
                ← Prev
              </button>
            )}

            <button
              onClick={currentStep < steps.length - 1 ? nextStep : endTutorial}
              className="px-4 py-2 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-lg hover:from-blue-600 hover:to-indigo-700 transition-all text-sm font-medium shadow-md"
            >
              {currentStep < steps.length - 1 ? 'Next →' : 'Finish'}
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default TutorialOverlay;