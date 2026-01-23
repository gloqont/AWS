"""
Guardrails for GLOQONT Decision Engine

This module implements checks and validations to ensure decisions meet the
strict requirements of the canonical decision output contract.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re
from enum import Enum


class GuardrailViolation(Enum):
    NO_DOWNBEAT_FIRST = "no_downbeat_first"
    UNCERTAINTY_NOT_EXPRESSED = "uncertainty_not_expressed"
    NUMERICAL_ADVICE_PRESENT = "numerical_advice_present"
    PROBABILITIES_STATED_AS_FACTS = "probabilities_stated_as_facts"
    CERTAINTY_CLAIMED = "certainty_claimed"
    VAGUE_INPUT_DETECTED = "vague_input_detected"
    MISSING_CRITICAL_INFO = "missing_critical_info"
    RISK_NOT_PROMINENT = "risk_not_prominent"


@dataclass
class GuardrailCheckResult:
    """Result of a guardrail check"""
    is_valid: bool
    violations: List[GuardrailViolation]
    warnings: List[str]
    suggestions: List[str]


class DecisionGuardrails:
    """Implements guardrails to ensure decision quality"""
    
    def __init__(self):
        # Patterns that indicate violations
        self.violation_patterns = {
            GuardrailViolation.NUMERICAL_ADVICE_PRESENT: [
                r'\b(should buy|should sell|buy \d+|sell \d+|invest \d+%|allocate \d+%)',
                r'(target return|expected return|guaranteed|assured)',
                r'(\d+\.?\d*\s*(%|percent|points|basis points))'
            ],
            GuardrailViolation.CERTAINTY_CLAIMED: [
                r'\b(guarantee|guaranteed|certain|certainly|definitely|sure to|will definitely)',
                r'\b(must|have to|need to|essential to)',
                r'(without doubt|for sure|absolutely certain)'
            ],
            GuardrailViolation.PROBABILITIES_STATED_AS_FACTS: [
                r'\b(will happen|will occur|will rise|will fall|will increase|will decrease)',
                r'\b(is sure|is definite|is guaranteed|is certain)',
                r'(expect with certainty|know for sure)'
            ],
            GuardrailViolation.VAGUE_INPUT_DETECTED: [
                r'\b(something|thing|stuff|that|this|it|some investment|random thing)',
                r'\b(market|stocks|bonds|investing|trading)\b.*\b(should|could|might)\b',
                r'(do something|make money|get rich|become wealthy)'
            ]
        }
    
    def check_decision_input(self, decision_text: str) -> GuardrailCheckResult:
        """
        Check if decision input meets guardrail requirements
        
        Args:
            decision_text: The decision text to check
            
        Returns:
            GuardrailCheckResult with validation results
        """
        violations = []
        warnings = []
        suggestions = []
        
        # Check for violation patterns
        for violation_type, patterns in self.violation_patterns.items():
            for pattern in patterns:
                if re.search(pattern, decision_text.lower()):
                    violations.append(violation_type)
                    break
        
        # Check for overly vague inputs
        if self._is_vague_input(decision_text):
            violations.append(GuardrailViolation.VAGUE_INPUT_DETECTED)
        
        # Check for missing critical information
        if self._has_missing_critical_info(decision_text):
            violations.append(GuardrailViolation.MISSING_CRITICAL_INFO)
        
        # Generate warnings and suggestions
        if not violations:
            is_valid = True
            warnings = self._generate_warnings(decision_text)
            suggestions = self._generate_suggestions(decision_text)
        else:
            is_valid = False
            # Add specific warnings for each violation
            for violation in violations:
                warnings.extend(self._get_violation_warnings(violation))
                suggestions.extend(self._get_violation_suggestions(violation))
        
        return GuardrailCheckResult(
            is_valid=is_valid,
            violations=violations,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def check_real_life_decision(self, real_life_decision: Dict[str, str]) -> GuardrailCheckResult:
        """
        Check if a RealLifeDecision meets the canonical output requirements

        Args:
            real_life_decision: The RealLifeDecision object as dictionary

        Returns:
            GuardrailCheckResult with validation results
        """
        violations = []
        warnings = []
        suggestions = []

        # Check that all required sections are present
        required_sections = [
            'decision_summary', 'why_this_helps', 'what_you_gain',
            'what_you_risk', 'when_this_stops_working', 'who_this_is_for'
        ]

        for section in required_sections:
            if section not in real_life_decision or not real_life_decision[section]:
                violations.append(GuardrailViolation.MISSING_CRITICAL_INFO)

        # ENFORCE DOWNBEAT-FIRST LOGIC: No upside may be shown unless downside is shown first and stronger
        if 'what_you_risk' in real_life_decision and 'what_you_gain' in real_life_decision:
            risk_section = real_life_decision['what_you_risk']
            gain_section = real_life_decision['what_you_gain']

            # Risk section should be at least as detailed as gain section
            if len(risk_section) < len(gain_section):
                violations.append(GuardrailViolation.RISK_NOT_PROMINENT)

            # Check if risk is mentioned more prominently than gain
            risk_words = len(re.findall(r'\brisk\b|\bdanger\b|\bloss\b|\bdownside\b|\bfail\b|\bthreat\b|\bcatastrophe\b|\bcrash\b|\bdecline\b|\bnegative\b', risk_section.lower()))
            gain_words = len(re.findall(r'\bgain\b|\bprofit\b|\bgrowth\b|\bopportun|\bbenefit\b|\bupside\b|\bpositive\b|\bincrease\b|\breturn\b', gain_section.lower()))

            # Risk should have more explicit risk-related terms
            if risk_words < gain_words:
                violations.append(GuardrailViolation.RISK_NOT_PROMINENT)

        # Check for certainty language in any section
        all_text = " ".join(real_life_decision.values()).lower()
        for violation_type, patterns in self.violation_patterns.items():
            if violation_type in [GuardrailViolation.CERTAINTY_CLAIMED,
                                GuardrailViolation.PROBABILITIES_STATED_AS_FACTS]:
                for pattern in patterns:
                    if re.search(pattern, all_text):
                        violations.append(violation_type)
                        break

        # Check for numerical advice
        for section_name, section_text in real_life_decision.items():
            if section_name not in ['decision_summary', 'who_this_is_for']:  # Allow some sections to be more descriptive
                for pattern in self.violation_patterns[GuardrailViolation.NUMERICAL_ADVICE_PRESENT]:
                    if re.search(pattern, section_text.lower()):
                        violations.append(GuardrailViolation.NUMERICAL_ADVICE_PRESENT)
                        break

        # Generate warnings and suggestions
        if not violations:
            is_valid = True
            warnings = self._generate_decision_warnings(real_life_decision)
            suggestions = self._generate_decision_suggestions(real_life_decision)
        else:
            is_valid = False
            for violation in violations:
                warnings.extend(self._get_violation_warnings(violation))
                suggestions.extend(self._get_violation_suggestions(violation))

        return GuardrailCheckResult(
            is_valid=is_valid,
            violations=violations,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _is_vague_input(self, decision_text: str) -> bool:
        """Check if the decision input is too vague"""
        text_lower = decision_text.lower().strip()
        
        # Very short inputs are likely vague
        if len(text_lower.split()) < 3:
            return True
        
        # Check for extremely generic terms
        generic_terms = [
            'something', 'anything', 'whatever', 'that thing', 
            'some investment', 'the market', 'stocks', 'it'
        ]
        
        # Count generic terms vs specific terms
        generic_count = sum(1 for term in generic_terms if term in text_lower)
        words = text_lower.split()
        
        # If more than half the content is generic, it's vague
        return generic_count > len(words) // 2
    
    def _has_missing_critical_info(self, decision_text: str) -> bool:
        """Check if critical information is missing"""
        text_lower = decision_text.lower()
        
        # Look for action words without targets
        action_patterns = [
            r'\b(buy|sell|invest|trade|hold|increase|decrease)\b(?!\s+[A-Z]{1,5}\b)',
            r'\b(go long|go short|enter position)\b(?!\s+(in|on)\s+\w+)',
        ]
        
        for pattern in action_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    def _generate_warnings(self, decision_text: str) -> List[str]:
        """Generate warnings for decision text"""
        warnings = []
        
        # Check if risk is mentioned prominently
        text_lower = decision_text.lower()
        risk_mentions = len(re.findall(r'\brisk\b|\bdanger\b|\bloss\b|\bdownside\b', text_lower))
        opportunity_mentions = len(re.findall(r'\bgain\b|\bprofit\b|\bgrowth\b|\bopportun', text_lower))
        
        if risk_mentions < opportunity_mentions:
            warnings.append("Risk considerations should be more prominent than opportunity mentions")
        
        return warnings
    
    def _generate_suggestions(self, decision_text: str) -> List[str]:
        """Generate suggestions for improving decision text"""
        suggestions = []
        
        # Suggest focusing on consequences rather than predictions
        if re.search(r'\bwill\b|\bexpect\b|\bguarantee\b', decision_text.lower()):
            suggestions.append("Focus on potential consequences rather than predictions")
        
        return suggestions
    
    def _generate_decision_warnings(self, real_life_decision: Dict[str, str]) -> List[str]:
        """Generate warnings for RealLifeDecision"""
        warnings = []
        
        # Check balance between risk and reward sections
        risk_len = len(real_life_decision.get('what_you_risk', ''))
        gain_len = len(real_life_decision.get('what_you_gain', ''))
        
        if risk_len < gain_len:
            warnings.append("Risk section should be more detailed than gain section")
        
        # Check that 'when this stops working' is specific
        when_stops = real_life_decision.get('when_this_stops_working', '').lower()
        if len(when_stops) < 20 or 'if' not in when_stops:
            warnings.append("When this stops working section should include specific failure conditions")
        
        return warnings
    
    def _generate_decision_suggestions(self, real_life_decision: Dict[str, str]) -> List[str]:
        """Generate suggestions for RealLifeDecision"""
        suggestions = []
        
        # Suggest more specific failure conditions
        when_stops = real_life_decision.get('when_this_stops_working', '')
        if 'if' not in when_stops.lower():
            suggestions.append("Include specific 'if-then' failure conditions in 'when this stops working'")
        
        # Suggest clearer user segmentation
        who_for = real_life_decision.get('who_this_is_for', '').lower()
        if 'beginner' not in who_for and 'expert' not in who_for and 'intermediate' not in who_for:
            suggestions.append("Clearly specify which user experience levels this decision is appropriate for")
        
        return suggestions
    
    def _get_violation_warnings(self, violation: GuardrailViolation) -> List[str]:
        """Get warnings for specific violations"""
        warning_map = {
            GuardrailViolation.NO_DOWNBEAT_FIRST: ["Downside must be shown before upside"],
            GuardrailViolation.UNCERTAINTY_NOT_EXPRESSED: ["Uncertainty must be expressed in all outputs"],
            GuardrailViolation.NUMERICAL_ADVICE_PRESENT: ["Numerical advice is not allowed in canonical output"],
            GuardrailViolation.PROBABILITIES_STATED_AS_FACTS: ["Probabilities should not be stated as facts"],
            GuardrailViolation.CERTAINTY_CLAIMED: ["Certainty should never be claimed"],
            GuardrailViolation.VAGUE_INPUT_DETECTED: ["Input is too vague to provide meaningful analysis"],
            GuardrailViolation.MISSING_CRITICAL_INFO: ["Critical information is missing from decision"],
            GuardrailViolation.RISK_NOT_PROMINENT: ["Risk considerations are not prominent enough"]
        }
        
        return warning_map.get(violation, [f"Violation detected: {violation.value}"])
    
    def _get_violation_suggestions(self, violation: GuardrailViolation) -> List[str]:
        """Get suggestions for fixing specific violations"""
        suggestion_map = {
            GuardrailViolation.NUMERICAL_ADVICE_PRESENT: [
                "Remove specific percentages, targets, or quantities",
                "Focus on qualitative outcomes rather than quantitative advice"
            ],
            GuardrailViolation.CERTAINTY_CLAIMED: [
                "Replace definitive language with conditional statements",
                "Acknowledge uncertainty and alternative outcomes"
            ],
            GuardrailViolation.PROBABILITIES_STATED_AS_FACTS: [
                "Frame potential outcomes as possibilities, not certainties",
                "Use language like 'may', 'might', 'could' instead of 'will'"
            ],
            GuardrailViolation.VAGUE_INPUT_DETECTED: [
                "Provide more specific details about the decision",
                "Include specific assets, strategies, or actions"
            ],
            GuardrailViolation.RISK_NOT_PROMINENT: [
                "Make risk considerations more detailed and prominent",
                "Lead with potential downsides before mentioning benefits"
            ]
        }
        
        return suggestion_map.get(violation, [f"Suggestions needed for: {violation.value}"])


class InputValidator:
    """Validates user inputs before processing"""
    
    def __init__(self):
        self.guardrails = DecisionGuardrails()
    
    def validate_decision_input(self, decision_text: str) -> GuardrailCheckResult:
        """Validate decision input text"""
        return self.guardrails.check_decision_input(decision_text)
    
    def validate_portfolio_data(self, portfolio_data: Dict[str, Any]) -> GuardrailCheckResult:
        """Validate portfolio data structure"""
        violations = []
        warnings = []
        suggestions = []
        
        # Check required fields
        required_fields = ['positions', 'total_value']
        for field in required_fields:
            if field not in portfolio_data:
                violations.append(GuardrailViolation.MISSING_CRITICAL_INFO)
        
        # Check positions structure
        positions = portfolio_data.get('positions', [])
        if not positions:
            violations.append(GuardrailViolation.MISSING_CRITICAL_INFO)
        
        for pos in positions:
            if 'ticker' not in pos or 'weight' not in pos:
                violations.append(GuardrailViolation.MISSING_CRITICAL_INFO)
        
        # Check total value is positive
        total_value = portfolio_data.get('total_value', 0)
        if total_value <= 0:
            violations.append(GuardrailViolation.MISSING_CRITICAL_INFO)
        
        return GuardrailCheckResult(
            is_valid=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            suggestions=suggestions
        )


# Global instance for use in decision engine
GUARDRAILS = DecisionGuardrails()
INPUT_VALIDATOR = InputValidator()