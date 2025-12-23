


class MovingAverageStrategy(Strategies):
    def __init__(self, conn: IBKRConnection, symbol: str, fast_period: int = 10, slow_period: int = 30):
        # Pass the connection object to the parent constructor
        super().__init__(conn=conn)
        self.symbol = symbol
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.contract = Stock(symbol, 'SMART', 'USD')
        print(f"Moving Average Strategy initialized for {symbol} ({fast_period}/{slow_period} periods).")

    def analyze_data(self, df: pd.DataFrame) -> Optional[str]:
        """Calculates MAs and generates a trade signal."""
        ib = self._conn.get_ib()
        if df is None or df.empty:
            return None

        # 1. Calculate Moving Averages on the closing price
        df[f'SMA_{self.fast_period}'] = df['close'].rolling(self.fast_period).mean()
        df[f'SMA_{self.slow_period}'] = df['close'].rolling(self.slow_period).mean()
        
        # Drop initial rows where MAs are NaN
        df.dropna(inplace=True) 

        if df.empty:
            return None

        df['Signal'] = 0

        # When 20-day SMA crosses above 50-day SMA
        df.loc[(df[f'SMA_{self.fast_period}'] > df[f'SMA_{self.slow_period}']) & (df[f'SMA_{self.fast_period}'].shift(1) < df[f'SMA_{self.slow_period}'].shift(1)), 'Signal'] = 1
        # When 20-day SMA crosses below 50-day SMA
        df.loc[(df[f'SMA_{self.fast_period}'] < df[f'SMA_{self.slow_period}']) & (df[f'SMA_{self.fast_period}'].shift(1) > df[f'SMA_{self.slow_period}'].shift(1)), 'Signal'] = -1

        # Create columns for plotting buy and sell signals at the close price
        df['Buy_Signal_Price'] = df.loc[df['Signal'] == 1, 'close']
        df['Sell_Signal_Price'] = df.loc[df['Signal'] == -1, 'close']

        # 2. Determine Signal (based on the last complete bar)
        last_fast = df[f'SMA_{self.fast_period}'].iloc[-1]
        last_slow = df[f'SMA_{self.slow_period}'].iloc[-1]
        
        # Check current position (simplified check)
        # Note: A real implementation would need to monitor the portfolio continuously.
        portfolio = ib.portfolio()
        current_position = next((item.position for item in portfolio if item.contract.symbol == self.symbol), 0)

        signal = None
        if last_fast > last_slow and current_position <= 0:
            # Fast MA crossed above Slow MA (Buy Signal)
            signal = 'BUY'
        elif last_fast < last_slow and current_position > 0:
            # Fast MA crossed below Slow MA (Sell/Close Signal)
            signal = 'SELL'
            
        print(f"Analysis: Fast MA: {last_fast:.2f}, Slow MA: {last_slow:.2f}, Signal: {signal}")
        self.df = df
        return signal

    def plot_signals(self, df: pd.DataFrame):
        df = self.df
        # 3. Visualize the Results
        plt.figure(figsize=(14, 7))

        # Plot closing price
        plt.plot(df['date'], df['close'], label='Close Price', color='blue', alpha=0.6)

        # Plot moving averages
        plt.plot(df['date'], df[f'SMA_{self.fast_period}'], label=f'{self.fast_period}-day SMA', color='green', linestyle='--')
        plt.plot(df['date'], df[f'SMA_{self.slow_period}'], label=f'{self.slow_period}-day SMA', color='red', linestyle='--')

        # Plot buy signals
        plt.scatter(df['date'], df['Buy_Signal_Price'], marker='^', color='green', s=100, label='Buy Signal', zorder=5)
        # Plot sell signals
        plt.scatter(df['date'], df['Sell_Signal_Price'], marker='v', color='red', s=100, label='Sell Signal', zorder=5)


        plt.title('AAPL Moving Average Crossover Strategy')
        plt.xlabel('Date')
        plt.ylabel('Price (USD)')
        plt.legend()
        plt.grid(True)
        plt.show()

    def run_strategy(self):
        """Main execution method for the strategy."""
        
        # 1. Get the necessary historical data
        data = self.get_data(
            self.contract, 
            durationStr="60 D", 
            barSizeSetting="1 hour"
        )
        
        if data is None:
            print("Could not retrieve data. Strategy halted.")
            return

        # 2. Analyze the data and get a signal
        signal = self.analyze_data(data)
        
        # 3. Execute the trade based on the signal
        if signal == 'BUY':
            # self.place_order(self.contract, 'BUY', quantity=10)
            print(f"Placing BUY order for {self.symbol}.")
        elif signal == 'SELL':
            # In this simple example, we assume we sell our entire position (10 shares)
            # self.place_order(self.contract, 'SELL', quantity=10) 
            print(f"Placing SELL order for {self.symbol}.")
        else:
            print(f"No trade signal generated for {self.symbol}.")
    
    def test_strategy(self):
        df = self.df.copy()
        df['Asset_Return'] = (1 + df['close'].pct_change()).cumprod() 
        df['Strategy_Return'] = (1+ \
                                 df['close'].pct_change() * (df['Signal'].shift(1)*-1)).cumprod()

        plt.figure(figsize=(14,7))
        plt.plot(df['date'], df['Asset_Return'], label='Asset Return', color='blue')
        plt.plot(df['date'], df['Strategy_Return'], label='Strategy Return', color='orange')
        plt.title('Strategy vs Asset Return')
        return df