"""
Enhanced Decision Classifier for GLOQONT Decision Intelligence Engine

This module implements the enhanced decision classification logic that properly
distinguishes between:
1. trade_decision (single-asset or directional)
2. portfolio_rebalancing (multi-asset / objective-based)

Based on the behavioral ground truth specifications provided.
"""

import re
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass


class DecisionCategory(Enum):
    TRADE_DECISION = "trade_decision"
    PORTFOLIO_REBALANCING = "portfolio_rebalancing"

@dataclass
class EnhancedDecisionClassification:
    """Enhanced classification result for a decision"""
    category: DecisionCategory
    action: str  # buy, sell, short, hedge, rebalance, etc.
    asset: str  # ticker symbol
    allocation_change: float  # percentage change (+ for buy, - for sell)
    confidence: float
    keywords_identified: List[str]
    asset_exists_in_portfolio: bool = False


class EnhancedDecisionClassifier:
    """Enhanced classifier that follows the behavioral ground truth"""

    def __init__(self):
        # Trade decision patterns - single asset directional trades
        self.trade_patterns = {
            # Simple buy/sell patterns
            r'\b(buy|purchase|add|increase|boost)\s+([A-Z]{1,5})\s+(\d+\.\d*)\s*(?:%|percent|pct)': ('buy', 2, 3),
            r'\b(sell|reduce|trim|decrease|exit|close)\s+(half of|all of|part of)?\s*([A-Z]{1,5})': ('sell', 3, None),
            r'\b(sell|reduce|trim|decrease|exit|close)\s+([A-Z]{1,5})\s*(\d+\.\d*)\s*(?:%|percent|pct)': ('sell', 2, 3),
            r'\b(go heavy on|load up on|pile into)\s+([A-Z]{1,5})': ('buy', 2, None),  # Implies aggressive buy
            r'\b(trim|reduce|cut back on)\s+([A-Z]{1,5})\s*(a bit|slightly|somewhat)?': ('sell', 2, None),
            r'\b(short|bet against|fade)\s+([A-Z]{1,5})\s*(\d+\.\d*)\s*(?:%|percent|pct)': ('short', 2, 3),
            r'\b(exit|completely sell|fully divest from)\s+([A-Z]{1,5})': ('sell', 2, None),
            
            # Patterns without explicit percentages but implying specific actions
            r'\b(buy|purchase|add|increase)\s+([A-Z]{1,5})': ('buy', 2, None),
            r'\b(sell|reduce|trim|decrease)\s+([A-Z]{1,5})': ('sell', 2, None),
        }

        # Portfolio rebalancing patterns - objective-based, multi-asset, strategic
        self.rebalancing_patterns = [
            r'\b(reduce my risk|lower portfolio risk|decrease risk|mitigate risk)',
            r'\b(move out of|rotate from|shift away from)\s+\w+\s+(into|toward|to)\s+\w+',
            r'\b(rebalance portfolio for|prepare for recession|defensive stance|capital preservation)',
            r'\b(optimize for long term growth|growth focus|growth oriented)',
            r'\b(I want to protect my capital|preserve capital|capital preservation)',
            r'\b(I might need cash|liquidity need|access funds)',
            r'\b(too much in one stock|concentration risk|diversify holdings)',
            r'\b(hedge my|protect against|shield from)\s+\w+\s+exposure',  # This is rebalancing, not single trade
            r'\b(diversify|spread investments|reduce concentration)',
            r'\b(balance|rebalance|redistribute|realloc|tilt portfolio)',
            r'\b(macro|market regime|economic cycle|interest rate|inflation hedge)',
        ]

        # Keywords that indicate trade decisions
        self.trade_keywords = [
            'buy', 'sell', 'purchase', 'add', 'increase', 'reduce', 'trim', 'decrease',
            'exit', 'close', 'short', 'go long', 'go short', 'load up', 'pile into',
            'cut back', 'fade', 'bet against', 'exit completely'
        ]

        # Keywords that indicate portfolio rebalancing
        self.rebalancing_keywords = [
            'reduce risk', 'lower risk', 'hedge exposure', 'rebalance', 'diversify',
            'rotate sectors', 'macro', 'regime', 'capital preservation', 'long term growth',
            'protect capital', 'liquidity', 'concentration', 'optimize', 'defensive',
            'recession', 'interest rate', 'inflation', 'balance portfolio', 'realloc'
        ]

    def classify_decision(self, decision_text: str, portfolio_data: Dict[str, Any] = None) -> EnhancedDecisionClassification:
        """Classify a decision according to the enhanced taxonomy that distinguishes
        between trade decisions and portfolio rebalancing.

        Args:
            decision_text: The decision text to classify
            portfolio_data: Optional portfolio data for context

        Returns:
            EnhancedDecisionClassification object with classification results
        """
        decision_lower = decision_text.lower()
        original_decision = decision_text

        # First, check for trade decision patterns
        trade_match_result = self._match_trade_patterns(decision_text)
        if trade_match_result:
            action, asset, allocation_change_pct = trade_match_result
            
            # Check if asset exists in portfolio
            asset_exists = self._check_asset_in_portfolio(asset, portfolio_data) if portfolio_data else False
            
            # Calculate confidence based on pattern match strength
            confidence = 0.9  # Strong confidence for explicit pattern matches
            
            return EnhancedDecisionClassification(
                category=DecisionCategory.TRADE_DECISION,
                action=action,
                asset=asset,
                allocation_change=allocation_change_pct,
                confidence=confidence,
                keywords_identified=[action, asset],
                asset_exists_in_portfolio=asset_exists
            )

        # Check for portfolio rebalancing patterns
        rebalancing_match_result = self._match_rebalancing_patterns(decision_text)
        if rebalancing_match_result:
            action, keywords = rebalancing_match_result
            
            # For rebalancing, we don't have a single asset, so use a generic identifier
            return EnhancedDecisionClassification(
                category=DecisionCategory.PORTFOLIO_REBALANCING,
                action=action,
                asset="MULTI_ASSET_STRATEGY",  # Indicates multi-asset approach
                allocation_change=0.0,  # Not applicable for rebalancing
                confidence=0.85,  # High confidence for rebalancing pattern matches
                keywords_identified=keywords,
                asset_exists_in_portfolio=False
            )

        # If no specific pattern matches, use keyword-based classification
        category, confidence, keywords = self._classify_by_keywords(decision_lower)
        
        # For keyword-based classification, we need to update the decision engine to extract asset info
        asset = self._extract_asset_from_text(decision_text)
        action = self._infer_action_from_text(decision_text)
        allocation_change = self._infer_allocation_change_from_text(decision_text)
        
        asset_exists = self._check_asset_in_portfolio(asset, portfolio_data) if asset and portfolio_data else False

        return EnhancedDecisionClassification(
            category=category,
            action=action,
            asset=asset or "UNKNOWN",
            allocation_change=allocation_change,
            confidence=confidence,
            keywords_identified=keywords,
            asset_exists_in_portfolio=asset_exists
        )

    def _match_trade_patterns(self, decision_text: str) -> Optional[tuple]:
        """Match decision text against trade decision patterns.
        
        Returns:
            Tuple of (action, asset, allocation_change_pct) or None if no match
        """
        decision_lower = decision_text.lower()
        
        for pattern, capture_groups in self.trade_patterns.items():
            match = re.search(pattern, decision_lower)
            if match:
                action = capture_groups[0]
                asset_idx = capture_groups[1]
                pct_idx = capture_groups[2]
                
                asset = match.group(asset_idx) if asset_idx and len(match.groups()) >= asset_idx else "UNKNOWN"
                
                # Handle allocation change
                allocation_change = 0.0
                if pct_idx and len(match.groups()) >= pct_idx:
                    try:
                        allocation_change = float(match.group(pct_idx))
                        # Apply negative sign for sell/short actions
                        if action in ['sell', 'short']:
                            allocation_change = -allocation_change
                    except (ValueError, IndexError):
                        allocation_change = 0.0
                else:
                    # Infer allocation change from context
                    if 'heavy' in decision_lower or 'load up' in decision_lower or 'pile into' in decision_lower:
                        allocation_change = 15.0  # Aggressive buy assumption
                    elif 'bit' in decision_lower or 'slightly' in decision_lower or 'somewhat' in decision_lower:
                        allocation_change = 3.0  # Small change assumption
                    elif 'half' in decision_lower:
                        allocation_change = 50.0  # Half position assumption
                    elif 'completely' in decision_lower or 'fully' in decision_lower:
                        allocation_change = 100.0  # Full exit assumption
                    else:
                        allocation_change = 5.0  # Default moderate change
        
                return action, asset, allocation_change
        
        return None

    def _match_rebalancing_patterns(self, decision_text: str) -> Optional[tuple]:
        """Match decision text against portfolio rebalancing patterns.
        
        Returns:
            Tuple of (action, keywords) or None if no match
        """
        decision_lower = decision_text.lower()
        
        for pattern in self.rebalancing_patterns:
            if re.search(pattern, decision_lower):
                # Determine action based on the pattern matched
                if any(word in decision_lower for word in ['reduce risk', 'lower risk', 'decrease risk', 'mitigate risk']):
                    action = 'risk_reduction'
                elif any(word in decision_lower for word in ['hedge my', 'protect against', 'shield from']):
                    action = 'hedging_strategy'
                elif any(word in decision_lower for word in ['rebalance portfolio for', 'recession', 'defensive']):
                    action = 'defensive_rebalancing'
                elif any(word in decision_lower for word in ['long term growth', 'growth focus']):
                    action = 'growth_oriented_rebalancing'
                elif any(word in decision_lower for word in ['protect my capital', 'preserve capital']):
                    action = 'capital_preservation'
                elif any(word in decision_lower for word in ['liquidity', 'need cash']):
                    action = 'liquidity_focused'
                elif any(word in decision_lower for word in ['concentration', 'one stock']):
                    action = 'concentration_reduction'
                elif any(word in decision_lower for word in ['diversify', 'spread investments']):
                    action = 'diversification'
                elif any(word in decision_lower for word in ['rebalance', 'redistribute', 'realloc']):
                    action = 'portfolio_rebalancing'
                else:
                    action = 'strategic_rebalancing'
                
                # Extract relevant keywords
                keywords = [word for word in self.rebalancing_keywords if word in decision_lower]
                
                return action, keywords
        
        return None

    def _classify_by_keywords(self, decision_lower: str) -> tuple:
        """Classify decision based on keyword presence.
        
        Returns:
            Tuple of (category, confidence, keywords)
        """
        trade_keywords_found = [kw for kw in self.trade_keywords if kw in decision_lower]
        rebalancing_keywords_found = [kw for kw in self.rebalancing_keywords if kw in decision_lower]
        
        # Count keyword matches
        trade_count = len(trade_keywords_found)
        rebalancing_count = len(rebalancing_keywords_found)
        
        if trade_count > rebalancing_count:
            # More trade keywords found
            confidence = min(0.8, 0.5 + (trade_count * 0.1))  # Increase confidence with more matches
            return DecisionCategory.TRADE_DECISION, confidence, trade_keywords_found
        elif rebalancing_count > trade_count:
            # More rebalancing keywords found
            confidence = min(0.8, 0.5 + (rebalancing_count * 0.1))
            return DecisionCategory.PORTFOLIO_REBALANCING, confidence, rebalancing_keywords_found
        else:
            # Equal counts or none found - default to trade decision for single assets
            # Check if there's a specific asset mentioned
            asset_pattern = r'\b([A-Z]{1,5})\b'
            assets_found = re.findall(asset_pattern, decision_lower.upper())
            
            if len(assets_found) == 1:
                # Single asset mentioned - likely a trade decision
                return DecisionCategory.TRADE_DECISION, 0.6, [assets_found[0]]
            else:
                # Multiple assets or no clear asset - likely rebalancing
                return DecisionCategory.PORTFOLIO_REBALANCING, 0.6, ["portfolio_strategy"]

    def _extract_asset_from_text(self, decision_text: str) -> Optional[str]:
        """Extract asset ticker from decision text."""
        # Look for common ticker patterns (1-5 uppercase letters, possibly with suffixes)
        ticker_pattern = r'\b([A-Z]{1,5}(?:\.[A-Z]{1,3})?)\b'
        matches = re.findall(ticker_pattern, decision_text.upper())
        
        # Return the first match, or None if no matches
        return matches[0] if matches else None

    def _infer_action_from_text(self, decision_text: str) -> str:
        """Infer action from decision text."""
        decision_lower = decision_text.lower()
        
        if any(word in decision_lower for word in ['buy', 'purchase', 'add', 'increase', 'boost', 'load up', 'pile into']):
            return 'buy'
        elif any(word in decision_lower for word in ['sell', 'reduce', 'trim', 'decrease', 'exit', 'close', 'cut back']):
            return 'sell'
        elif any(word in decision_lower for word in ['short', 'bet against', 'fade']):
            return 'short'
        elif any(word in decision_lower for word in ['hedge', 'protect', 'shield']):
            return 'hedge'
        elif any(word in decision_lower for word in ['rebalance', 'rotate', 'diversify', 'optimize']):
            return 'rebalance'
        else:
            return 'unknown'

    def _infer_allocation_change_from_text(self, decision_text: str) -> float:
        """Infer allocation change from decision text."""
        decision_lower = decision_text.lower()
        
        # Look for explicit percentages
        percent_pattern = r'(\d+\.\d*)\s*(?:%|percent|pct)'
        percent_match = re.search(percent_pattern, decision_lower)
        
        if percent_match:
            try:
                pct = float(percent_match.group(1))
                # Determine sign based on action
                if any(word in decision_lower for word in ['sell', 'reduce', 'trim', 'decrease', 'exit']):
                    return -pct
                else:
                    return pct
            except ValueError:
                pass
        
        # Infer from context words
        if 'heavy' in decision_lower or 'aggressive' in decision_lower:
            return 15.0  # Large position
        elif 'bit' in decision_lower or 'slightly' in decision_lower or 'small' in decision_lower:
            return 3.0   # Small change
        elif 'half' in decision_lower:
            return 50.0  # Half position
        elif 'completely' in decision_lower or 'fully' in decision_lower:
            return 100.0 # Full position
        else:
            return 5.0   # Default moderate change

    def _check_asset_in_portfolio(self, asset: str, portfolio_data: Dict[str, Any]) -> bool:
        """Check if asset exists in the portfolio."""
        if not portfolio_data or 'positions' not in portfolio_data:
            return False
        
        positions = portfolio_data['positions']
        for pos in positions:
            if pos.get('ticker', '').upper() == asset.upper():
                return True
        
        return False


# Global instance for use in decision engine
ENHANCED_DECISION_CLASSIFIER = EnhancedDecisionClassifier()
