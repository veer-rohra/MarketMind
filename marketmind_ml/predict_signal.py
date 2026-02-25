#!/usr/bin/env python3
import argparse
import json

import joblib
import pandas as pd

from train_marketmind import engineer_features


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate MarketMind action signals.")
    parser.add_argument("--model", required=True, help="Path to joblib model bundle")
    parser.add_argument("--input", required=True, help="CSV containing inference rows")
    parser.add_argument(
        "--latest-only",
        action="store_true",
        help="Only output the latest row per ticker",
    )
    parser.add_argument(
        "--output",
        default="marketmind_signals.csv",
        help="Path to save generated signals",
    )
    parser.add_argument(
        "--thresholds-file",
        default="",
        help="Optional JSON file containing signal thresholds",
    )
    parser.add_argument(
        "--enter-threshold",
        type=float,
        default=None,
        help="Override enter_pred_return threshold",
    )
    parser.add_argument(
        "--exit-threshold",
        type=float,
        default=None,
        help="Override exit_pred_return threshold",
    )
    parser.add_argument(
        "--risk-threshold",
        type=float,
        default=None,
        help="Override high_risk_volatility threshold",
    )
    return parser.parse_args()


def action_from_prediction(pred_return: float, risk_vol: float, thresholds: dict) -> str:
    if risk_vol >= thresholds["high_risk_volatility"] and pred_return <= thresholds["enter_pred_return"]:
        return "AVOID"
    if pred_return >= thresholds["enter_pred_return"] and risk_vol < thresholds["high_risk_volatility"]:
        return "ENTER"
    if pred_return <= thresholds["exit_pred_return"]:
        return "EXIT"
    return "WAIT"


def resolve_thresholds(bundle: dict, args: argparse.Namespace) -> dict:
    thresholds = dict(bundle.get("signal_thresholds", {}))

    if args.thresholds_file:
        with open(args.thresholds_file, "r", encoding="utf-8") as f:
            file_thresholds = json.load(f)
        thresholds.update(file_thresholds)

    if args.enter_threshold is not None:
        thresholds["enter_pred_return"] = args.enter_threshold
    if args.exit_threshold is not None:
        thresholds["exit_pred_return"] = args.exit_threshold
    if args.risk_threshold is not None:
        thresholds["high_risk_volatility"] = args.risk_threshold

    required = {"enter_pred_return", "exit_pred_return", "high_risk_volatility"}
    missing = required - set(thresholds.keys())
    if missing:
        raise ValueError(f"Missing thresholds: {sorted(missing)}")
    return thresholds


def main() -> None:
    args = parse_args()
    bundle = joblib.load(args.model)
    pipeline = bundle["pipeline"]
    feature_columns = bundle["feature_columns"]
    signal_thresholds = resolve_thresholds(bundle, args)
    raw = pd.read_csv(args.input)
    data = engineer_features(raw)

    if args.latest_only:
        data["date"] = pd.to_datetime(data["date"])
        data = data.sort_values(["ticker", "date"]).groupby("ticker", as_index=False).tail(1)

    usable = data.dropna(subset=feature_columns).copy()
    usable["pred_forward_return_5d"] = pipeline.predict(usable[feature_columns])
    usable["action"] = usable.apply(
        lambda r: action_from_prediction(
            pred_return=float(r["pred_forward_return_5d"]),
            risk_vol=float(r["volatility_20d"]),
            thresholds=signal_thresholds,
        ),
        axis=1,
    )

    output_columns = ["date", "ticker", "close", "volatility_20d", "pred_forward_return_5d", "action"]
    result = usable[output_columns].sort_values(["date", "ticker"])
    result.to_csv(args.output, index=False)

    print(f"Saved signals to: {args.output}")
    print(f"Thresholds: {signal_thresholds}")
    if not result.empty:
        print("Action counts:")
        print(result["action"].value_counts(dropna=False).to_string())
    print(result.tail(20).to_string(index=False))


if __name__ == "__main__":
    main()
