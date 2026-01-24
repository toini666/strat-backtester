import plotly.graph_objects as go
import pandas as pd
from ..engine.backtester import BacktestResult

class ResultsVisualizer:
    """
    Visualizes backtest results using Plotly.
    """
    
    def summary_table(self, result: BacktestResult) -> pd.DataFrame:
        """
        Create a summary metrics table.
        """
        metrics = {
            "Total Return [%]": f"{result.total_return * 100:.2f}%",
            "Sharpe Ratio": f"{result.sharpe_ratio:.2f}",
            "Max Drawdown [%]": f"{result.max_drawdown * 100:.2f}%",
            "Win Rate [%]": f"{result.win_rate * 100:.1f}%",
            "Profit Factor": f"{result.profit_factor:.2f}",
            "Total Trades": result.total_trades
        }
        
        return pd.DataFrame([metrics]).T.rename(columns={0: "Value"})
        
    def plot_equity_curve(self, result: BacktestResult) -> go.Figure:
        """
        Plot equity curve and drawdown.
        """
        cum_returns = result.portfolio.cumulative_returns()
        drawdown = result.portfolio.drawdown()
        
        fig = go.Figure()
        
        # Equity
        fig.add_trace(go.Scatter(
            x=cum_returns.index, 
            y=cum_returns,
            mode='lines',
            name='Equity'
        ))
        
        # Drawdown
        fig.add_trace(go.Scatter(
            x=drawdown.index,
            y=drawdown,
            mode='lines',
            name='Drawdown',
            fill='tozeroy',
            line=dict(color='red', width=1),
            opacity=0.3
        ))
        
        fig.update_layout(
            title='Equity Curve & Drawdown',
            xaxis_title='Date',
            yaxis_title='Return',
            template='plotly_dark'
        )
        return fig
    
    def plot_trades(self, result: BacktestResult) -> go.Figure:
        """
        Plot price with entry/exit markers.
        """
        data = result.data
        entries = result.portfolio.entries.vbt.signals.fshift(1) # Shift to match execution? VBT signals are typically boolean. 
        # Actually VBT signals align with execution if we are careful.
        # But for plotting on Close price, we usually want to mark the bar where signal happened (Close).
        
        # VBT Portfolio holds trade records too.
        
        fig = go.Figure()
        
        # Price
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['Close'],
            mode='lines',
            name='Price',
            line=dict(color='gray')
        ))
        
        # Entries
        entry_mask = result.portfolio.entries
        entry_pts = data.loc[entry_mask]
        if not entry_pts.empty:
            fig.add_trace(go.Scatter(
                x=entry_pts.index,
                y=entry_pts['Close'],
                mode='markers',
                name='Entry',
                marker=dict(symbol='triangle-up', size=10, color='lime')
            ))
            
        # Exits
        exit_mask = result.portfolio.exits
        exit_pts = data.loc[exit_mask]
        if not exit_pts.empty:
             fig.add_trace(go.Scatter(
                x=exit_pts.index,
                y=exit_pts['Close'],
                mode='markers',
                name='Exit',
                marker=dict(symbol='triangle-down', size=10, color='red')
            ))
            
        fig.update_layout(
            title='Trade Entries & Exits',
            template='plotly_dark'
        )
        return fig
