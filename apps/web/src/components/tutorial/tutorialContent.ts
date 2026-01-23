import { TutorialStep } from './TutorialContext';

// Define tutorial steps for the first-time user onboarding
export const FIRST_TIME_TUTORIAL_STEPS: TutorialStep[] = [
  {
    id: 'portfolio-optimizer',
    title: 'Portfolio Optimizer',
    description: 'This section allows you to build and optimize your investment portfolio. You can add stocks, set quantities, and define your risk budget. Click Next to explore this section in detail with a comprehensive walkthrough.',
    elementId: 'portfolio-optimizer-link',
  },
  {
    id: 'scenario-simulation',
    title: 'Scenario Simulation',
    description: 'Simulate different market scenarios to understand how your portfolio might perform under various conditions. Click Next to explore this section in detail with a comprehensive walkthrough.',
    elementId: 'scenario-simulation-link',
  },
  {
    id: 'tax-advisor',
    title: 'Tax Advisor',
    description: 'Get personalized tax-saving recommendations based on your portfolio and tax residency. Click Next to explore this section in detail with a comprehensive walkthrough.',
    elementId: 'tax-advisor-link',
  },
  {
    id: 'tax-impact',
    title: 'Tax Impact',
    description: 'Analyze the tax implications of your investment decisions before making them. Click Next to explore this section in detail with a comprehensive walkthrough.',
    elementId: 'tax-impact-link',
  }
];

// Define tutorial steps for the portfolio optimizer page
export const PORTFOLIO_OPTIMIZER_TUTORIAL: TutorialStep[] = [
  {
    id: 'portfolio-name',
    title: 'Portfolio Name',
    description: 'Give your portfolio a name to easily identify it later.',
    elementId: 'portfolio-name-input',
  },
  {
    id: 'risk-budget',
    title: 'Risk Budget',
    description: 'Select your risk tolerance level. This affects how the optimizer allocates your investments.',
    elementId: 'risk-budget-selector',
  },
  {
    id: 'total-value',
    title: 'Total Portfolio Value',
    description: 'This is calculated automatically based on the quantities and current market prices of your holdings.',
    elementId: 'total-portfolio-value',
  },
  {
    id: 'allocation',
    title: 'Total Allocation',
    description: 'Your portfolio must sum to 100%. The optimizer will validate this before processing.',
    elementId: 'total-allocation',
  },
  {
    id: 'positions-table',
    title: 'Positions Table',
    description: 'Add your stock positions here. Enter ticker symbols and quantities. The system will fetch current prices automatically.',
    elementId: 'positions-table',
  },
  {
    id: 'validate-button',
    title: 'Validate Button',
    description: 'Click this to validate your portfolio before saving or optimizing.',
    elementId: 'validate-button',
  }
];

// Define tutorial steps for the tax advisor page
export const TAX_ADVISOR_TUTORIAL: TutorialStep[] = [
  {
    id: 'tax-country',
    title: 'Tax Residency',
    description: 'Select your tax residency country to get accurate tax recommendations.',
    elementId: 'tax-country-selector',
  },
  {
    id: 'generate-advice',
    title: 'Generate Advice',
    description: 'Click this button to receive personalized tax-saving recommendations based on your portfolio.',
    elementId: 'generate-advice-button',
  },
  {
    id: 'recommendations',
    title: 'Recommendations',
    description: 'These are personalized suggestions to help minimize your tax liability.',
    elementId: 'recommendations-section',
  }
];

// Define tutorial steps for the scenario simulation page
export const SCENARIO_SIMULATION_TUTORIAL: TutorialStep[] = [
  {
    id: 'scenario-portfolio-summary',
    title: 'Current Portfolio',
    description: 'This shows your current portfolio that will be used for the scenario simulation. The simulation will analyze how your decision impacts this portfolio.',
    elementId: 'scenario-portfolio-summary',
  },
  {
    id: 'decision-type-selector',
    title: 'Decision Type',
    description: 'Choose between Trade Decision (for buying stocks not in your portfolio) or Portfolio Rebalancing (for adjusting existing holdings).',
    elementId: 'decision-type-selector',
  },
  {
    id: 'decision-input',
    title: 'Decision Input',
    description: 'Describe the decision you want to simulate. For example, "Buy NVDA 5%" or "Sell AAPL 10% and buy GOOGL".',
    elementId: 'decision-input',
  },
  {
    id: 'tax-country-and-actions',
    title: 'Tax Country and Actions',
    description: 'Select your tax country for the simulation and click "Run Scenario" to execute the analysis.',
    elementId: 'tax-country-and-actions',
  },
  {
    id: 'run-scenario-button',
    title: 'Run Scenario Button',
    description: 'Click this button to run the scenario simulation and see the potential outcomes.',
    elementId: 'run-scenario-button',
  }
];

// Define tutorial steps for the tax impact page
export const TAX_IMPACT_TUTORIAL: TutorialStep[] = [
  {
    id: 'tax-decision-info',
    title: 'Decision Information',
    description: 'Shows the last decision you simulated in the Scenario Simulation tool. This is used to calculate tax implications.',
    elementId: 'tax-decision-info',
  },
  {
    id: 'tax-residency-selector',
    title: 'Tax Residency',
    description: 'Select your tax residency country to get accurate tax impact calculations based on local tax laws.',
    elementId: 'tax-residency-selector',
  },
  {
    id: 'portfolio-value-display',
    title: 'Portfolio Value',
    description: 'Shows the current value of your portfolio and expected returns before tax.',
    elementId: 'portfolio-value-display',
  },
  {
    id: 'estimated-tax-payable',
    title: 'Estimated Tax Payable',
    description: 'This is the estimated amount of tax you might owe based on the simulated decision and your tax residency.',
    elementId: 'estimated-tax-payable',
  },
  {
    id: 'effective-tax-rate',
    title: 'Effective Tax Rate',
    description: 'This represents the overall tax rate applied to your portfolio based on the decision and your tax residency.',
    elementId: 'effective-tax-rate',
  },
  {
    id: 'after-tax-impact',
    title: 'After-Tax Impact',
    description: 'Shows the expected return after accounting for taxes. The tax drag shows how much the taxes reduce your returns.',
    elementId: 'after-tax-impact',
  }
];
