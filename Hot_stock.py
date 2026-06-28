import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

class MarketScreener:
    def __init__(self, stock_universe: list):
        """
        Initialize with a list of tickers to scan (e.g., Nifty 50, Bank Nifty, or a custom sector list)
        """
        self.stock_universe = stock_universe

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        """
        Convert a base NSE ticker like RELIANCE into Yahoo Finance format RELIANCE.NS.
        """
        symbol = symbol.strip().upper()
        if symbol.endswith((".NS", ".BO", ".NSE", ".BSE")):
            return symbol
        return f"{symbol}.NS"

    def scan_market(self) -> pd.DataFrame:
        """
        Scans the stock universe for unusual volume spikes and strong momentum breakout signals.
        """
        hot_stocks = []

        print(f"Starting live Indian market scan for {len(self.stock_universe)} tickers...")

        for symbol in self.stock_universe:
            try:
                normalized_symbol = self.normalize_symbol(symbol)
                ticker = yf.Ticker(normalized_symbol)
                df = ticker.history(period="3mo", interval="1d")

                if df.empty or len(df) < 20:
                    continue

                # --- 1. Unusual Volume Calculation ---
                # Calculate the average volume over the last 20 trading days (excluding today)
                avg_volume_20d = df['Volume'].iloc[-21:-1].mean()
                latest_volume = df['Volume'].iloc[-1]
                
                # Volume ratio: 1.5x means volume is 50% higher than average
                volume_ratio = latest_volume / avg_volume_20d if avg_volume_20d > 0 else 0

                # --- 2. Momentum & Breakout Calculation ---
                latest_close = df['Close'].iloc[-1]
                prev_close = df['Close'].iloc[-2]
                daily_return_pct = ((latest_close - prev_close) / prev_close) * 100

                # 20-day Simple Moving Average (SMA)
                df['SMA_20'] = df['Close'].rolling(window=20).mean()
                latest_sma20 = df['SMA_20'].iloc[-1]

                # Price relative to its 52-week or recent high
                highest_high_2m = df['High'].iloc[-21:-1].max()
                is_breaking_out = latest_close > highest_high_2m

                # --- 3. Screening Logic (Defining "Hot") ---
                # Criteria: Either an extraordinary volume surge OR a combination of a price jump and high volume
                is_hot = False
                reason = []

                if volume_ratio >= 2.0:
                    is_hot = True
                    reason.append(f"Massive volume spike ({round(volume_ratio, 1)}x baseline)")
                
                if is_breaking_out and daily_return_pct > 1.5:
                    is_hot = True
                    reason.append("Price breakout above 2-month local high")

                if daily_return_pct > 4.0 and volume_ratio > 1.2:
                    is_hot = True
                    reason.append(f"Strong momentum jump (+{round(daily_return_pct, 1)}%) on high volume")

                if is_hot:
                    hot_stocks.append({
                        "Ticker": normalized_symbol,
                        "Price": round(latest_close, 2),
                        "Daily Change %": round(daily_return_pct, 2),
                        "Volume Multiplier": round(volume_ratio, 2),
                        "Above 20-SMA": latest_close > latest_sma20,
                        "Trigger Reason": " & ".join(reason)
                    })

            except Exception as e:
                # Keep scanning if a single ticker fails due to network or API limits
                print(f"Skipping {symbol}: {str(e)}")
                continue

        # Convert to DataFrame, sort by highest volume multiplier & change
        if hot_stocks:
            screener_df = pd.DataFrame(hot_stocks)
            screener_df = screener_df.sort_values(by=["Volume Multiplier", "Daily Change %"], ascending=False)
            return screener_df
        else:
            return pd.DataFrame()

    def plot_results(self, shortlist: pd.DataFrame, output_path: str = "hot_stock_visualization.png") -> str:
        """
        Create a simple bar chart of the shortlisted stocks' daily moves and save it to disk.
        """
        if shortlist.empty:
            return ""

        fig, ax = plt.subplots(figsize=(10, 5))
        colors = ["#2ca02c" if value >= 0 else "#d62728" for value in shortlist["Daily Change %"]]
        bars = ax.bar(shortlist["Ticker"], shortlist["Daily Change %"], color=colors)

        ax.set_title("Hot Stock Daily Change")
        ax.set_ylabel("Daily Change (%)")
        ax.axhline(0, color="black", linewidth=0.8)
        ax.tick_params(axis="x", labelrotation=45)
        plt.tight_layout()

        for bar, volume_multiplier in zip(bars, shortlist["Volume Multiplier"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{volume_multiplier:.1f}x",
                ha="center",
                va="bottom",
                fontsize=8,
            )

        fig.savefig(output_path, dpi=200)
        plt.close(fig)
        return output_path

# --- Quick Test Execution ---
if __name__ == "__main__":
    # Sample Indian market watch list for a live-style NSE scan
    sample_universe = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "BHARTIARTL", "LT", "KOTAKBANK", "AXISBANK"]
    
    screener = MarketScreener(stock_universe=sample_universe)
    shortlist = screener.scan_market()
    
    print("\n=== HOT STOCK SHORTLIST ===")
    if not shortlist.empty:
        print(shortlist.to_string(index=False))
        chart_path = screener.plot_results(shortlist, output_path="indian_market_scan.png")
        if chart_path:
            print(f"\nVisualization saved to {chart_path}")
    else:
        print("Market is quiet. No hot stock triggers found matching the criteria.")