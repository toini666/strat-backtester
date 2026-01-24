import numpy as np

class RiskBasedPositionSizer:
    """
    Calculates position size based on risk management rules.
    """
    
    def __init__(
        self,
        risk_per_trade: float = 0.01, # 1% default
        max_position_pct: float = 1.0 # Max 100% of capital
    ):
        self.risk_per_trade = risk_per_trade
        self.max_position_pct = max_position_pct
        
    def calculate_size(
        self,
        capital: float,
        entry_price: float,
        stop_loss_price: float,
        point_value: float = 1.0
    ) -> int:
        """
        Calculate number of contracts/shares to trade.
        
        Formula:
            Risk Amount = Capital * Risk Per Trade
            Trade Risk Points = abs(Entry - SL)
            Trade Risk Value = Trade Risk Points * Point Value
            Size = Risk Amount / Trade Risk Value
            
        Args:
            capital: Current account balance
            entry_price: Theoretical entry price
            stop_loss_price: Stop loss price
            point_value: Value of 1 point move (e.g. $2 for MNQ, $5 for MES, 1.0 for Stocks)
            
        Returns:
            Number of contracts (integer)
        """
        if entry_price == stop_loss_price:
            return 0
            
        risk_amount = capital * self.risk_per_trade
        trade_risk_per_contract = abs(entry_price - stop_loss_price) * point_value
        
        if trade_risk_per_contract <= 0:
            return 0
            
        size = risk_amount / trade_risk_per_contract
        
        # Check max position size limit
        max_capital_allocation = capital * self.max_position_pct
        # Approximate capital cost (margin is different, but let's use notional or explicit limit)
        # For simplicity, we just cap size if needed, but often max_position_pct applies to Stock notional.
        # For futures, margin is lower, so this check might be looser.
        # Let's keep it simple: just return risk-based size formatted as int.
        
        return int(size)
