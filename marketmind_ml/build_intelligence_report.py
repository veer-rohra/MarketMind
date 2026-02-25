#!/usr/bin/env python3
import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build MarketMind A-E intelligence report.")
    parser.add_argument("--live-data", default="marketmind_ml/live_market_data.csv")
    parser.add_argument("--signals", default="marketmind_signals.csv")
    parser.add_argument("--portfolio", default="marketmind_portfolio_plan.csv")
    parser.add_argument("--output", default="marketmind_intelligence_report.md")
    return parser.parse_args()


def pct(v: float) -> str:
    if pd.isna(v):
        return "n/a"
    return f"{v:.2%}"


def num(v: float, d: int = 2) -> str:
    if pd.isna(v):
        return "n/a"
    return f"{v:.{d}f}"


def latest_rows(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    x["date"] = pd.to_datetime(x["date"])
    return x.sort_values(["ticker", "date"]).groupby("ticker", as_index=False).tail(1).sort_values("ticker")


def main() -> None:
    args = parse_args()
    live = pd.read_csv(args.live_data)
    signals = pd.read_csv(args.signals)
    portfolio = pd.read_csv(args.portfolio)

    latest = latest_rows(live)
    merged = latest.merge(
        signals[["ticker", "action", "pred_forward_return_5d"]],
        on="ticker",
        how="left",
    )

    lines = ["# MarketMind Intelligence Report", ""]

    if not portfolio.empty:
        lines.extend(["## Top Ranked Positions", ""])
        for _, r in portfolio.sort_values("rank").head(5).iterrows():
            lines.append(
                f"- {int(r['rank'])}. {r['ticker']} | {r['action']} | Pred5D {pct(r['pred_forward_return_5d'])} | "
                f"Vol {pct(r['volatility_20d'])} | Weight {pct(r['allocation_weight'])}"
            )
        lines.append("")

    for _, r in merged.iterrows():
        t = r["ticker"]
        lines.extend([f"## {t}", ""])
        lines.extend(
            [
                "### A) Real-Time Market Data",
                f"- Live stock price: {num(r.get('close'))}",
                f"- Volume changes: {pct(r.get('volume_change_1d'))}",
                f"- Volatility (20d): {pct(r.get('volatility_20d'))}",
                f"- Market depth (proxy): {num(r.get('market_depth_proxy'), 0)}",
                f"- Breakouts and breakdowns: breakout={int(r.get('breakout_20d', 0))}, breakdown={int(r.get('breakdown_20d', 0))}",
                "",
                "### B) Technical Indicators",
                f"- Moving averages: MA20={num(r.get('ma_20'))}, MA50={num(r.get('ma_50'))}, MA200={num(r.get('ma_200'))}",
                f"- RSI(14): {num(r.get('rsi_14'))}",
                f"- MACD: line={num(r.get('macd'))}, signal={num(r.get('macd_signal'))}, hist={num(r.get('macd_hist'))}",
                f"- Support & resistance: support={num(r.get('support_20d'))}, resistance={num(r.get('resistance_20d'))}",
                f"- Trend reversals: {int(r.get('trend_reversal_flag', 0))}",
                "",
                "### C) Fundamental Data",
                f"- P/E ratio: {num(r.get('pe_ratio'))}",
                f"- Earnings reports (days to next): {num(r.get('days_to_next_earnings'), 0)}",
                f"- Revenue growth: {pct(r.get('revenue_growth_qoq'))}",
                f"- Debt levels (D/E): {num(r.get('debt_to_equity'))}",
                f"- Cash flow: operating={num(r.get('operating_cashflow'), 0)}, free={num(r.get('free_cashflow'), 0)}",
                "- Quarterly results: represented by EPS QoQ growth",
                f"- EPS growth QoQ: {pct(r.get('eps_growth_qoq'))}",
                "",
                "### D) News & Sentiment",
                f"- Breaking financial news: {num(r.get('breaking_news_count'), 0)} headline hits",
                f"- Company announcements: {num(r.get('announcement_count'), 0)} headline hits",
                f"- Government policy impact: {num(r.get('policy_impact_score'), 0)} policy-related hits",
                f"- Social media/news sentiment score: {num(r.get('sentiment_score'))}",
                f"- Market rumors vs confirmed updates: rumor/confirmed ratio={num(r.get('rumor_confirmed_ratio'))}",
                "",
                "### E) Macro Environment",
                f"- Interest rate changes (10Y proxy): {pct(r.get('interest_rate_10y'))}",
                f"- Inflation data (FRED latest): {num(r.get('inflation_yoy'))}",
                f"- Sector-wide performance (1d): {pct(r.get('sector_return_1d'))}",
                f"- Global market signals (1d): {pct(r.get('global_return_1d'))}",
                f"- Decision: action={r.get('action', 'n/a')} | Pred 5D return={pct(r.get('pred_forward_return_5d'))}",
                "",
            ]
        )

    Path(args.output).write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved intelligence report: {args.output}")


if __name__ == "__main__":
    main()
