import pandas as pd
import numpy as np
import matplotlib as plt

class QuantitativeEvaluator:
    """
    Calculates institutional-grade metrics from a strategy's equity curve.
    Assumes a standard 252 trading days in a year for annualization.
    """
    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate
        self.trading_days_per_year = 252

    def calculate_metrics(self, df: pd.DataFrame) -> dict:
        """
        Takes a DataFrame containing at least 'close' and 'Strategy_Return'
        and calculates core performance metrics.
        """
        # Calculate daily percentage returns from the cumulative strategy return
        df['Daily_Return'] = df['Strategy_Return'].pct_change()
        
        # 1. Total Return
        total_return = df['Strategy_Return'].iloc[-1] - 1.0

        # 2. Annualized Volatility
        daily_volatility = df['Daily_Return'].std()
        annual_volatility = daily_volatility * np.sqrt(self.trading_days_per_year)

        # 3. Sharpe Ratio
        # $S = \frac{R_p - R_f}{\sigma_p}$
        expected_annual_return = df['Daily_Return'].mean() * self.trading_days_per_year
        excess_return = expected_annual_return - self.risk_free_rate
        
        if annual_volatility > 0:
            sharpe_ratio = excess_return / annual_volatility
        else:
            sharpe_ratio = 0.0

        # 4. Sortino Ratio (Downside deviation only)
        negative_returns = df[df['Daily_Return'] < 0]['Daily_Return']
        downside_deviation = negative_returns.std() * np.sqrt(self.trading_days_per_year)
        
        if downside_deviation > 0:
            sortino_ratio = excess_return / downside_deviation
        else:
            sortino_ratio = 0.0

        # 5. Maximum Drawdown
        # $MDD = \frac{\text{Trough Value} - \text{Peak Value}}{\text{Peak Value}}$
        df['Peak'] = df['Strategy_Return'].cummax()
        df['Drawdown'] = (df['Strategy_Return'] - df['Peak']) / df['Peak']
        max_drawdown = df['Drawdown'].min()

        # 6. Win Rate (Approximation based on daily positive movement for this vectorized example)
        winning_days = len(df[df['Daily_Return'] > 0])
        total_trading_days = len(df[df['Daily_Return'] != 0])
        win_rate = winning_days / total_trading_days if total_trading_days > 0 else 0

        metrics = {
            "Total Return": f"{total_return * 100:.2f}%",
            "Annualized Volatility": f"{annual_volatility * 100:.2f}%",
            "Sharpe Ratio": round(sharpe_ratio, 3),
            "Sortino Ratio": round(sortino_ratio, 3),
            "Max Drawdown": f"{max_drawdown * 100:.2f}%",
            "Win Rate (Days)": f"{win_rate * 100:.2f}%"
        }
        
        return metrics
    def plot_drawdown(self, df: pd.DataFrame):
        """Visualizes the underwater/drawdown curve."""
        if 'Drawdown' not in df.columns:
            df['Peak'] = df['Strategy_Return'].cummax()
            df['Drawdown'] = (df['Strategy_Return'] - df['Peak']) / df['Peak']

        plt.figure(figsize=(14, 5))
        plt.fill_between(df.index, df['Drawdown'], 0, color='red', alpha=0.3)
        plt.plot(df.index, df['Drawdown'], color='red', linewidth=1)
        plt.title('Strategy Drawdown (Underwater Curve)')
        plt.xlabel('Date')
        plt.ylabel('Drawdown %')
        plt.grid(True, alpha=0.3)
        plt.show()































# class QuantitativeEvaluator:
#     def calculate_metrics(self, equity_curve: list) -> dict:
#         if not equity_curve: return {}
        
#         df = pd.DataFrame(equity_curve).set_index('datetime')
#         df['Daily_Return'] = df['equity'].pct_change().fillna(0)
        
#         total_return = (df['equity'].iloc[-1] / df['equity'].iloc[0]) - 1.0
#         annual_volatility = df['Daily_Return'].std() * np.sqrt(252)
        
#         excess_return = (df['Daily_Return'].mean() * 252) - 0.02
#         sharpe_ratio = excess_return / annual_volatility if annual_volatility > 0 else 0.0
        
#         df['Peak'] = df['equity'].cummax()
#         df['Drawdown'] = (df['equity'] - df['Peak']) / df['Peak']
#         max_drawdown = df['Drawdown'].min()

#         return {
#             "Total Return": f"{total_return * 100:.2f}%",
#             "Sharpe Ratio": round(sharpe_ratio, 3),
#             "Max Drawdown": f"{max_drawdown * 100:.2f}%",
#             "Ending Equity": f"${df['equity'].iloc[-1]:.2f}"
#         }