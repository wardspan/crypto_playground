import pandas as pd
import numpy as np
from typing import Dict, List

class PortfolioAnalyzer:
    def __init__(self, db_session):
        self.db = db_session

    def calculate_metrics(self, portfolio_id: int) -> Dict:
        # Get historical data
        history = self.get_portfolio_history(portfolio_id)
        
        # Calculate key metrics
        returns = self.calculate_returns(history)
        volatility = self.calculate_volatility(history)
        sharpe_ratio = self.calculate_sharpe_ratio(returns, volatility)
        
        return {
            "total_return": returns,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "coin_correlations": self.calculate_correlations(history)
        }

    def get_rebalancing_suggestions(self, portfolio_id: int) -> List[Dict]:
        # Get current portfolio allocation
        current_allocation = self.get_current_allocation(portfolio_id)
        
        # Define target allocation (you might want to make this configurable)
        target_allocation = {
            'ethereum': 0.4,  # 40%
            'solana': 0.2,    # 20%
            'uniswap': 0.15,  # 15%
            'ripple': 0.1,    # 10%
            'lido-dao': 0.1,  # 10%
            'the-sandbox': 0.05  # 5%
        }
        
        suggestions = []
        for coin, current_pct in current_allocation.items():
            target_pct = target_allocation[coin]
            diff = target_pct - current_pct
            
            if abs(diff) > 0.05:  # 5% threshold for rebalancing
                action = "buy" if diff > 0 else "sell"
                suggestions.append({
                    "coin": coin,
                    "action": action,
                    "percentage": abs(diff),
                    "reason": f"Current allocation ({current_pct:.1%}) is {'below' if diff > 0 else 'above'} target ({target_pct:.1%})"
                })
        
        return suggestions

    def get_risk_assessment(self, portfolio_id: int) -> Dict:
        metrics = self.calculate_metrics(portfolio_id)
        
        risk_level = "medium"
        if metrics["volatility"] > 0.5:
            risk_level = "high"
        elif metrics["volatility"] < 0.2:
            risk_level = "low"
            
        return {
            "risk_level": risk_level,
            "volatility": metrics["volatility"],
            "sharpe_ratio": metrics["sharpe_ratio"],
            "recommendations": self.get_risk_recommendations(risk_level)
        } 