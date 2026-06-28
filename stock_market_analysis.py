import yfinance as yf
import pandas as pd
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


class MarketScreener:
    def __init__(self, stock_universe: list):
        self.stock_universe = stock_universe

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        symbol = symbol.strip().upper()
        if symbol.endswith((".NS", ".BO", ".NSE", ".BSE")):
            return symbol
        return f"{symbol}.NS"

    def scan_market(self) -> pd.DataFrame:
        hot_stocks = []
        print(f"Starting live Indian market scan for {len(self.stock_universe)} tickers...")

        for symbol in self.stock_universe:
            try:
                normalized_symbol = self.normalize_symbol(symbol)
                ticker = yf.Ticker(normalized_symbol)
                df = ticker.history(period="3mo", interval="1d")

                if df.empty or len(df) < 20:
                    continue

                avg_volume_20d = df['Volume'].iloc[-21:-1].mean()
                latest_volume = df['Volume'].iloc[-1]
                volume_ratio = latest_volume / avg_volume_20d if avg_volume_20d > 0 else 0

                latest_close = df['Close'].iloc[-1]
                prev_close = df['Close'].iloc[-2]
                daily_return_pct = ((latest_close - prev_close) / prev_close) * 100

                df['SMA_20'] = df['Close'].rolling(window=20).mean()
                latest_sma20 = df['SMA_20'].iloc[-1]

                highest_high_2m = df['High'].iloc[-21:-1].max()
                is_breaking_out = latest_close > highest_high_2m

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
                        "Trigger Reason": " & ".join(reason),
                    })

            except Exception as e:
                print(f"Skipping {symbol}: {str(e)}")
                continue

        if hot_stocks:
            screener_df = pd.DataFrame(hot_stocks)
            screener_df = screener_df.sort_values(by=["Volume Multiplier", "Daily Change %"], ascending=False)
            return screener_df
        return pd.DataFrame()

    def plot_results(self, shortlist: pd.DataFrame, output_path: str = "indian_market_scan.png") -> str:
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


if __name__ == "__main__":
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
