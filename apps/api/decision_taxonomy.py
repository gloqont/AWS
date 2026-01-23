"""
Decision Taxonomy for GLOQONT Decision Engine

This module implements explicit classification of decision types to better understand
their risk characteristics and implications.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import re


class DecisionType(Enum):
    RISK_INCREASING = "risk_increasing"
    RISK_REDUCING = "risk_reducing"
    RISK_SHIFTING = "risk_shifting"
    DIVERSIFICATION = "diversification"
    HEDGING = "hedging"
    CONCENTRATION = "concentration"
    LEVERAGE = "leverage"
    DELEVERAGE = "deleverage"
    REBALANCING = "rebalancing"
    TAX_LOSS_HARVESTING = "tax_loss_harvesting"
    POSITION_OPENING = "position_opening"
    POSITION_CLOSING = "position_closing"


class DecisionImpact(Enum):
    INCREASES_VOLATILITY = "increases_volatility"
    DECREASES_VOLATILITY = "decreases_volatility"
    INCREASES_CORRELATION = "increases_correlation"
    DECREASES_CORRELATION = "decreases_correlation"
    INCREASES_LIQUIDITY_RISK = "increases_liquidity_risk"
    DECREASES_LIQUIDITY_RISK = "decreases_liquidity_risk"
    INCREASES_CONCENTRATION = "increases_concentration"
    DECREASES_CONCENTRATION = "decreases_concentration"
    ADDS_LEVERAGE = "adds_leverage"
    REMOVES_LEVERAGE = "removes_leverage"


class Reversibility(Enum):
    REVERSIBLE = "reversible"
    IRREVERSIBLE = "irreversible"
    PARTIALLY_REVERSIBLE = "partially_reversible"


@dataclass
class DecisionClassification:
    """Classification result for a decision"""
    decision_type: DecisionType
    impact_types: List[DecisionImpact]
    reversibility: Reversibility
    confidence: float
    keywords_identified: List[str]
    primary_asset: Optional[str] = None
    secondary_assets: List[str] = None


class DecisionTaxonomyClassifier:
    """Classifies decisions according to the GLOQONT taxonomy"""
    
    def __init__(self):
        # Define decision type patterns
        self.type_patterns = {
            DecisionType.RISK_INCREASING: [
                r'\b(leverage|borrow|margin|credit)\b',
                r'\b(increase|add|more|boost|amplify)\b.*\b(risk|exposure|beta)\b',
                r'\b(high(er)?|significant|substantial)\b.*\b(risk|volatility)\b',
                r'\b(speculative|gamble|bet)\b'
            ],
            DecisionType.RISK_REDUCING: [
                r'\b(reduce|decrease|lower|cut|diminish)\b.*\b(risk|exposure|beta)\b',
                r'\b(low(er)?|minimal|minimize)\b.*\b(risk|volatility)\b',
                r'\b(conservative|defensive|safe)\b',
                r'\b(cash|treasury|bills|money market)\b'
            ],
            DecisionType.RISK_SHIFTING: [
                r'\b(shift|transfer|move|convert|transform)\b.*\b(risk|exposure)\b',
                r'\b(substitute|replace|swap)\b.*\b(asset|position)\b',
                r'\b(long|short)\b.*\b(position|exposure)\b'
            ],
            DecisionType.DIVERSIFICATION: [
                r'\b(diversif(y|ication)|spread|allocate|distribute)\b',
                r'\b(broaden|widen|expand)\b.*\b(portfolio|holdings)\b',
                r'\b(multi|various|different)\b.*\b(asset|investment|holding)\b'
            ],
            DecisionType.HEDGING: [
                r'\b(hedge|hedging|protection|insurance|shield|guard)\b',
                r'\b(offset|counter|against|cover)\b.*\b(risk|loss|decline)\b',
                r'\b(stop loss|collar|floor|cap)\b',
                r'\b(put|call|option|derivative)\b.*\b(protect|insurance)\b'
            ],
            DecisionType.CONCENTRATION: [
                r'\b(concentrate|focus|converge|single|only|sole)\b.*\b(position|holding|investment)\b',
                r'\b(all|majority|bulk)\b.*\b(in)\b.*\b(one|single|specific)\b',
                r'\b(heavy|large|significant)\b.*\b(position|allocation)\b.*\b(in)\b'
            ],
            DecisionType.LEVERAGE: [
                r'\b(leverage|borrow|margin|credit|loan|debt)\b',
                r'\b(borrow(ed)?|lend|credit)\b.*\b(to invest|for investment)\b',
                r'\b(margin|borrowed|debt)\b.*\b(invest|purchase)\b'
            ],
            DecisionType.DELEVERAGE: [
                r'\b(deleverage|pay down|reduce|eliminate|remove)\b.*\b(debt|leverage|margin)\b',
                r'\b(repay|settle|clear)\b.*\b(borrowed|margin|loan)\b',
                r'\b(cash|equity)\b.*\b(replace|substitute)\b.*\b(debt)\b'
            ],
            DecisionType.REBALANCING: [
                r'\b(rebalance|adjust|modify|change|redistribute)\b.*\b(allocation|weight|percentage)\b',
                r'\b(tilt|rotate|shift)\b.*\b(from|between)\b',
                r'\b(weight|allocation)\b.*\b(change|adjust|update)\b'
            ],
            DecisionType.TAX_LOSS_HARVESTING: [
                r'\b(tax loss|harvest|realize loss|sell at loss)\b',
                r'\b(loss|negative return)\b.*\b(sell|dispose|close)\b.*\b(for tax)\b',
                r'\b(capital loss|tax benefit)\b.*\b(sell|realize)\b'
            ],
            DecisionType.POSITION_OPENING: [
                r'\b(buy|purchase|open|establish|initiate|enter|take)\b.*\b(position|investment|holding)\b',
                r'\b(go long|acquire|obtain|secure)\b',
                r'\b(new|first time)\b.*\b(investment|position)\b'
            ],
            DecisionType.POSITION_CLOSING: [
                r'\b(sell|close|exit|terminate|liquidate|dispose|realize)\b.*\b(position|investment|holding)\b',
                r'\b(go short|reverse|end|finish)\b',
                r'\b(full|complete)\b.*\b(sale|exit|closure)\b'
            ]
        }
        
        # Define impact patterns
        self.impact_patterns = {
            DecisionImpact.INCREASES_VOLATILITY: [
                r'\b(leverage|margin|borrowed funds)\b',
                r'\b(aggressive|high risk|volatile|speculative)\b',
                r'\b(single|concentrated|undiversified)\b.*\b(position)\b',
                r'\b(option|derivative|complex)\b.*\b(strategy)\b'
            ],
            DecisionImpact.DECREASES_VOLATILITY: [
                r'\b(diversif(y|ication)|broad|wide)\b',
                r'\b(stable|stable income|bond|fixed income)\b',
                r'\b(cash|money market|treasury)\b',
                r'\b(hedge|insurance|protection)\b'
            ],
            DecisionImpact.INCREASES_CONCENTRATION: [
                r'\b(single|one|only|sole)\b.*\b(asset|stock|sector)\b',
                r'\b(heavy|large|majority)\b.*\b(position|allocation)\b.*\b(in)\b',
                r'\b(concentrate|focus|converge)\b.*\b(on)\b'
            ],
            DecisionImpact.DECREASES_CONCENTRATION: [
                r'\b(diversif(y|ication)|spread|distribute)\b',
                r'\b(multiple|various|different)\b.*\b(assets|investments)\b',
                r'\b(broaden|expand|widen)\b.*\b(portfolio)\b'
            ],
            DecisionImpact.ADDS_LEVERAGE: [
                r'\b(leverage|margin|borrow|credit|debt)\b',
                r'\b(borrow(ed)?|loan|credit)\b.*\b(invest|buy)\b',
                r'\b(financed|leveraged)\b.*\b(purchase)\b'
            ],
            DecisionImpact.REMOVES_LEVERAGE: [
                r'\b(pay down|reduce|eliminate|repay)\b.*\b(debt|leverage|margin)\b',
                r'\b(cash|equity)\b.*\b(replace)\b.*\b(debt)\b'
            ]
        }
        
        # Define reversibility patterns
        self.reversibility_patterns = {
            Reversibility.REVERSIBLE: [
                r'\b(buy|sell|purchase|dispose)\b.*\b(public|listed|liquid)\b',
                r'\b(liquid|easily sold|tradable)\b.*\b(asset|security)\b',
                r'\b(exchange traded|mutual fund|etf)\b'
            ],
            Reversibility.IRREVERSIBLE: [
                r'\b(real estate|property|private equity|illiquid)\b',
                r'\b(long term|locked in|restricted|illiquid)\b.*\b(investment)\b',
                r'\b(private|unlisted|non-tradable)\b.*\b(asset)\b',
                r'\b(annuity|structured product|complex derivative)\b'
            ]
        }
    
    def classify_decision(self, decision_text: str, portfolio_data: Dict[str, Any] = None) -> DecisionClassification:
        """
        Classify a decision according to the GLOQONT taxonomy
        
        Args:
            decision_text: The decision text to classify
            portfolio_data: Optional portfolio data for context
            
        Returns:
            DecisionClassification object with classification results
        """
        decision_lower = decision_text.lower()
        
        # Identify decision type
        decision_type, type_confidence, type_keywords = self._identify_decision_type(decision_lower)
        
        # Identify impact types
        impact_types, impact_keywords = self._identify_impact_types(decision_lower)
        
        # Identify reversibility
        reversibility, rev_confidence, rev_keywords = self._identify_reversibility(decision_lower)
        
        # Extract primary and secondary assets
        primary_asset, secondary_assets = self._extract_assets(decision_text, portfolio_data)
        
        # Combine confidence scores (simple average for now)
        overall_confidence = (type_confidence + rev_confidence) / 2 if rev_confidence > 0 else type_confidence
        
        # Add keywords from all categories
        all_keywords = list(set(type_keywords + impact_keywords + rev_keywords))
        
        return DecisionClassification(
            decision_type=decision_type,
            impact_types=impact_types,
            reversibility=reversibility,
            confidence=overall_confidence,
            keywords_identified=all_keywords,
            primary_asset=primary_asset,
            secondary_assets=secondary_assets or []
        )
    
    def _identify_decision_type(self, decision_text: str) -> tuple:
        """Identify the primary decision type"""
        scores = {}
        matched_keywords = {}
        
        for dtype, patterns in self.type_patterns.items():
            score = 0
            keywords = []
            
            for pattern in patterns:
                matches = re.findall(pattern, decision_text)
                if matches:
                    score += len(matches)
                    keywords.extend(matches)
            
            if score > 0:
                scores[dtype] = score
                matched_keywords[dtype] = keywords
        
        if not scores:
            # Default to position opening if nothing matches
            return DecisionType.POSITION_OPENING, 0.3, ["default"]
        
        # Find the type with highest score
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        
        # Calculate confidence (normalize by total possible matches)
        total_matches = sum(scores.values())
        confidence = min(1.0, best_score / max(1, total_matches * 0.5))  # Adjust based on match density
        
        return best_type, confidence, matched_keywords.get(best_type, [])
    
    def _identify_impact_types(self, decision_text: str) -> tuple:
        """Identify the impact types of the decision"""
        impact_types = []
        all_keywords = []
        
        for impact, patterns in self.impact_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, decision_text)
                if matches:
                    impact_types.append(impact)
                    all_keywords.extend(matches)
                    break  # Only count each impact type once
        
        return impact_types, all_keywords
    
    def _identify_reversibility(self, decision_text: str) -> tuple:
        """Identify the reversibility characteristic"""
        scores = {}
        matched_keywords = {}
        
        for rev_type, patterns in self.reversibility_patterns.items():
            score = 0
            keywords = []
            
            for pattern in patterns:
                matches = re.findall(pattern, decision_text)
                if matches:
                    score += len(matches)
                    keywords.extend(matches)
            
            if score > 0:
                scores[rev_type] = score
                matched_keywords[rev_type] = keywords
        
        if not scores:
            # Default to reversible for most public securities
            return Reversibility.REVERSIBLE, 0.5, ["default_assumption"]
        
        # Find the type with highest score
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        
        # Calculate confidence
        total_matches = sum(scores.values())
        confidence = min(1.0, best_score / max(1, total_matches))
        
        return best_type, confidence, matched_keywords.get(best_type, [])
    
    def _extract_assets(self, decision_text: str, portfolio_data: Dict[str, Any] = None) -> tuple:
        """Extract primary and secondary assets mentioned in the decision"""
        # Look for ticker symbols (typically 1-5 uppercase letters)
        ticker_pattern = r'\b([A-Z]{1,5})\b'
        potential_tickers = re.findall(ticker_pattern, decision_text)
        
        # Filter based on context words that suggest buying/holding
        context_words = ['buy', 'sell', 'hold', 'increase', 'decrease', 'add', 'remove', 'invest', 'position']
        has_context = any(word in decision_text.lower() for word in context_words)
        
        if has_context and potential_tickers:
            primary = potential_tickers[0] if potential_tickers else None
            secondary = potential_tickers[1:] if len(potential_tickers) > 1 else []
            return primary, secondary
        
        # If no clear context, return None
        return None, []
    
    def get_decision_risk_profile(self, classification: DecisionClassification) -> Dict[str, Any]:
        """
        Get a risk profile based on the decision classification
        
        Args:
            classification: The decision classification
            
        Returns:
            Dictionary with risk profile information
        """
        risk_profile = {
            "risk_level": self._get_risk_level(classification),
            "complexity_level": self._get_complexity_level(classification),
            "time_horizon_implications": self._get_time_horizon_implications(classification),
            "liquidity_considerations": self._get_liquidity_considerations(classification),
            "concentration_warnings": self._get_concentration_warnings(classification),
            "leverage_alerts": self._get_leverage_alerts(classification)
        }
        
        return risk_profile
    
    def _get_risk_level(self, classification: DecisionClassification) -> str:
        """Determine risk level based on classification"""
        if DecisionImpact.INCREASES_VOLATILITY in classification.impact_types:
            return "HIGH"
        elif DecisionImpact.DECREASES_VOLATILITY in classification.impact_types:
            return "LOW"
        elif classification.decision_type in [DecisionType.LEVERAGE, DecisionType.RISK_INCREASING]:
            return "HIGH"
        elif classification.decision_type in [DecisionType.HEDGING, DecisionType.RISK_REDUCING]:
            return "LOW"
        else:
            return "MODERATE"
    
    def _get_complexity_level(self, classification: DecisionClassification) -> str:
        """Determine complexity level based on classification"""
        if classification.decision_type in [DecisionType.HEDGING, DecisionType.LEVERAGE, DecisionType.TAX_LOSS_HARVESTING]:
            return "HIGH"
        elif classification.decision_type in [DecisionType.DIVERSIFICATION, DecisionType.REBALANCING]:
            return "MODERATE"
        else:
            return "LOW"
    
    def _get_time_horizon_implications(self, classification: DecisionClassification) -> str:
        """Get time horizon implications"""
        if classification.decision_type in [DecisionType.TAX_LOSS_HARVESTING]:
            return "SHORT_TERM_FOCUS_NEEDED"
        elif classification.decision_type in [DecisionType.HEDGING]:
            return "MONITOR_HEDGE_EXPIRATION"
        else:
            return "ALIGN_WITH_INVESTMENT_OBJECTIVES"
    
    def _get_liquidity_considerations(self, classification: DecisionClassification) -> List[str]:
        """Get liquidity considerations"""
        considerations = []
        
        if classification.reversibility == Reversibility.IRREVERSIBLE:
            considerations.append("Position may be difficult to exit quickly")
        
        if DecisionImpact.INCREASES_LIQUIDITY_RISK in classification.impact_types:
            considerations.append("Decision may increase liquidity risk")
        
        return considerations
    
    def _get_concentration_warnings(self, classification: DecisionClassification) -> List[str]:
        """Get concentration warnings"""
        warnings = []
        
        if DecisionImpact.INCREASES_CONCENTRATION in classification.impact_types:
            warnings.append("Decision increases portfolio concentration risk")
        
        if classification.decision_type == DecisionType.CONCENTRATION:
            warnings.append("Decision explicitly concentrates portfolio in specific assets")
        
        return warnings
    
    def _get_leverage_alerts(self, classification: DecisionClassification) -> List[str]:
        """Get leverage alerts"""
        alerts = []
        
        if DecisionImpact.ADDS_LEVERAGE in classification.impact_types:
            alerts.append("Decision adds leverage to portfolio")
        
        if classification.decision_type == DecisionType.LEVERAGE:
            alerts.append("Decision explicitly involves leverage")
        
        return alerts


# Global instance for use in decision engine
DECISION_TAXONOMY_CLASSIFIER = DecisionTaxonomyClassifier()