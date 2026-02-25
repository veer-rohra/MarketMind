#!/usr/bin/env python3
import argparse
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic MarketMind training data.")
    parser.add_argument("--rows", type=int, default=2000, help="Total rows to create")
    parser.add_argument(
        "--output",
        default="sample_market_data.csv",
        help="Output CSV path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = np.random.default_rng(42)
    start = datetime(2020, 1, 1)

    rows = []
    for i in range(args.rows):
        ticker = TICKERS[i % len(TICKERS)]
        date = start + timedelta(days=i // len(TICKERS))

        market_ret = rng.normal(0.0006, 0.011)
        sector_ret = market_ret + rng.normal(0.0, 0.006)
        sentiment = float(np.clip(rng.normal(0.05, 0.35), -1, 1))
        vol20 = abs(rng.normal(0.028, 0.012))
        pe = max(5.0, rng.normal(28, 10))
        pb = max(0.8, rng.normal(8, 3))
        dte = max(0.0, rng.normal(1.2, 0.8))
        rev_growth = rng.normal(0.03, 0.06)
        eps_growth = rng.normal(0.025, 0.08)
        close = max(20, rng.normal(200, 120))
        volume = max(100_000, int(rng.normal(30_000_000, 8_000_000)))

        alpha = (
            0.35 * sentiment
            + 0.25 * rev_growth
            + 0.20 * eps_growth
            + 0.12 * market_ret
            + 0.08 * sector_ret
            - 0.08 * vol20
            - 0.015 * dte
            - 0.0007 * pe
            - 0.0009 * pb
        )
        target_forward_return_5d = alpha + rng.normal(0.0, 0.02)

        rows.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "ticker": ticker,
                "close": round(close, 2),
                "volume": int(volume),
                "market_return_1d": market_ret,
                "sector_return_1d": sector_ret,
                "sentiment_score": sentiment,
                "pe_ratio": pe,
                "pb_ratio": pb,
                "debt_to_equity": dte,
                "revenue_growth_qoq": rev_growth,
                "eps_growth_qoq": eps_growth,
                "volatility_20d": vol20,
                "target_forward_return_5d": target_forward_return_5d,
            }
        )

    df = pd.DataFrame(rows)
    df.to_csv(args.output, index=False)
    print(f"Synthetic data saved to: {args.output}")
    print(df.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
