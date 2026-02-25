#!/usr/bin/env python3
import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rank ENTER signals and allocate risk budget.")
    parser.add_argument("--signals", default="marketmind_signals.csv", help="Signals CSV from predict_signal.py")
    parser.add_argument(
        "--output",
        default="marketmind_portfolio_plan.csv",
        help="Output CSV with ranked allocations",
    )
    parser.add_argument(
        "--report-output",
        default="marketmind_portfolio_report.md",
        help="Output markdown report",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=100000.0,
        help="Total capital to allocate in dollars",
    )
    parser.add_argument(
        "--risk-budget",
        type=float,
        default=0.8,
        help="Fraction of capital allowed for active positions",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=8,
        help="Maximum number of positions",
    )
    parser.add_argument(
        "--max-position-weight",
        type=float,
        default=0.25,
        help="Maximum portfolio weight per position within active capital",
    )
    return parser.parse_args()


def stable_weight(score: pd.Series, max_position_weight: float) -> pd.Series:
    if score.sum() <= 0:
        return pd.Series(np.zeros(len(score)), index=score.index)

    weights = score / score.sum()
    clipped = weights.clip(upper=max_position_weight)
    if clipped.sum() <= 0:
        return clipped
    return clipped / clipped.sum()


def choose_candidates(df: pd.DataFrame, top_n: int) -> pd.DataFrame:
    enter = df[df["action"] == "ENTER"].copy()
    if not enter.empty:
        return enter.nlargest(top_n, "risk_adjusted_score")

    fallback = df[(df["action"] == "WAIT") & (df["pred_forward_return_5d"] > 0)].copy()
    return fallback.nlargest(top_n, "risk_adjusted_score")


def build_report(plan: pd.DataFrame, args: argparse.Namespace) -> str:
    used_capital = plan["allocated_capital_usd"].sum() if not plan.empty else 0.0
    lines = [
        "# MarketMind Portfolio Plan",
        "",
        f"- Capital: ${args.capital:,.2f}",
        f"- Risk budget: {args.risk_budget:.0%}",
        f"- Max positions: {args.top_n}",
        f"- Max position weight: {args.max_position_weight:.0%}",
        f"- Allocated capital: ${used_capital:,.2f}",
        "",
    ]

    if plan.empty:
        lines.extend(
            [
                "## No Actionable Positions",
                "",
                "No ENTER signals were available (or fallback WAIT signals were not positive).",
            ]
        )
        return "\n".join(lines) + "\n"

    lines.extend(["## Ranked Positions", "", "| Rank | Ticker | Action | Pred 5D Return | Volatility | Weight | Capital |", "|---:|---|---|---:|---:|---:|---:|"])
    for _, row in plan.iterrows():
        lines.append(
            f"| {int(row['rank'])} | {row['ticker']} | {row['action']} | {row['pred_forward_return_5d']:.2%} | "
            f"{row['volatility_20d']:.2%} | {row['allocation_weight']:.2%} | ${row['allocated_capital_usd']:,.2f} |"
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    signals = pd.read_csv(args.signals)
    required = {"ticker", "action", "pred_forward_return_5d", "volatility_20d"}
    missing = required - set(signals.columns)
    if missing:
        raise ValueError(f"Signals file missing columns: {sorted(missing)}")

    signals["volatility_20d"] = signals["volatility_20d"].replace(0, np.nan)
    signals["risk_adjusted_score"] = (
        signals["pred_forward_return_5d"].clip(lower=0) / signals["volatility_20d"].fillna(1e-6)
    )
    signals["risk_adjusted_score"] = signals["risk_adjusted_score"].replace([np.inf, -np.inf], 0.0).fillna(0.0)

    candidates = choose_candidates(signals, args.top_n).copy()
    candidates = candidates.sort_values("risk_adjusted_score", ascending=False).reset_index(drop=True)

    active_capital = max(args.capital * args.risk_budget, 0.0)
    candidates["allocation_weight"] = stable_weight(candidates["risk_adjusted_score"], args.max_position_weight)
    candidates["allocated_capital_usd"] = candidates["allocation_weight"] * active_capital
    candidates["rank"] = np.arange(1, len(candidates) + 1)

    output_columns = [
        "rank",
        "ticker",
        "action",
        "pred_forward_return_5d",
        "volatility_20d",
        "risk_adjusted_score",
        "allocation_weight",
        "allocated_capital_usd",
    ]
    plan = candidates[output_columns] if not candidates.empty else pd.DataFrame(columns=output_columns)
    plan.to_csv(args.output, index=False)

    report_text = build_report(plan, args)
    Path(args.report_output).write_text(report_text, encoding="utf-8")

    print(f"Saved portfolio plan: {args.output}")
    print(f"Saved portfolio report: {args.report_output}")
    if not plan.empty:
        print(plan.to_string(index=False))
    else:
        print("No actionable positions were found.")


if __name__ == "__main__":
    main()
