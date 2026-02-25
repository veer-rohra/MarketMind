#!/usr/bin/env python3
import argparse
import json

import joblib
import numpy as np
import pandas as pd

from predict_signal import action_from_prediction
from train_marketmind import engineer_features, validate_columns


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tune MarketMind signal thresholds from labeled historical data.")
    parser.add_argument("--model", required=True, help="Path to trained model artifact")
    parser.add_argument("--input", required=True, help="Historical labeled CSV with target_forward_return_5d")
    parser.add_argument(
        "--target-enter-rate",
        type=float,
        default=0.25,
        help="Desired share of rows classified as ENTER",
    )
    parser.add_argument(
        "--output-thresholds",
        default="marketmind_ml/tuned_thresholds.json",
        help="Where to save tuned threshold JSON",
    )
    parser.add_argument(
        "--update-model",
        action="store_true",
        help="Write tuned thresholds into the model artifact too",
    )
    return parser.parse_args()


def score_thresholds(df: pd.DataFrame, target_enter_rate: float, thresholds: dict) -> tuple[float, dict]:
    actions = df.apply(
        lambda r: action_from_prediction(
            pred_return=float(r["pred_forward_return_5d"]),
            risk_vol=float(r["volatility_20d"]),
            thresholds=thresholds,
        ),
        axis=1,
    )
    temp = df.copy()
    temp["action"] = actions

    enter = temp[temp["action"] == "ENTER"]
    exit_rows = temp[temp["action"] == "EXIT"]
    avoid = temp[temp["action"] == "AVOID"]

    enter_rate = float((temp["action"] == "ENTER").mean())
    enter_avg = float(enter["target_forward_return_5d"].mean()) if not enter.empty else -0.05
    enter_win_rate = float((enter["target_forward_return_5d"] > 0).mean()) if not enter.empty else 0.0
    exit_avg = float(exit_rows["target_forward_return_5d"].mean()) if not exit_rows.empty else 0.0
    avoid_bad_rate = float((avoid["target_forward_return_5d"] < 0).mean()) if not avoid.empty else 0.0

    # Objective: high quality ENTER picks, reasonable ENTER frequency, sensible EXIT/AVOID behavior.
    score = (
        (enter_avg * 100.0)
        + (enter_win_rate * 2.0)
        + (max(-exit_avg, 0.0) * 40.0)
        + (avoid_bad_rate * 1.5)
        - (abs(enter_rate - target_enter_rate) * 6.0)
    )
    stats = {
        "score": score,
        "enter_rate": enter_rate,
        "enter_avg_forward_5d": enter_avg,
        "enter_win_rate": enter_win_rate,
        "exit_avg_forward_5d": exit_avg,
        "avoid_negative_hit_rate": avoid_bad_rate,
        "rows": int(len(temp)),
    }
    return score, stats


def main() -> None:
    args = parse_args()
    bundle = joblib.load(args.model)

    raw = pd.read_csv(args.input)
    validate_columns(raw)
    data = engineer_features(raw).dropna(subset=["target_forward_return_5d"]).copy()

    feature_columns = bundle["feature_columns"]
    usable = data.dropna(subset=feature_columns).copy()
    usable["pred_forward_return_5d"] = bundle["pipeline"].predict(usable[feature_columns])

    enter_grid = np.linspace(0.005, 0.045, 9)
    exit_grid = np.linspace(-0.03, -0.004, 14)
    risk_grid = np.linspace(0.03, 0.08, 11)

    best_score = -1e18
    best_thresholds = None
    best_stats = {}

    for enter_t in enter_grid:
        for exit_t in exit_grid:
            if exit_t >= enter_t:
                continue
            for risk_t in risk_grid:
                thresholds = {
                    "enter_pred_return": float(enter_t),
                    "exit_pred_return": float(exit_t),
                    "high_risk_volatility": float(risk_t),
                }
                score, stats = score_thresholds(usable, args.target_enter_rate, thresholds)
                if score > best_score:
                    best_score = score
                    best_thresholds = thresholds
                    best_stats = stats

    if best_thresholds is None:
        raise RuntimeError("Threshold tuning failed to find a valid candidate.")

    with open(args.output_thresholds, "w", encoding="utf-8") as f:
        json.dump(best_thresholds, f, indent=2)

    if args.update_model:
        bundle["signal_thresholds"] = best_thresholds
        joblib.dump(bundle, args.model)

    print(f"Saved tuned thresholds: {args.output_thresholds}")
    print(json.dumps(best_thresholds, indent=2))
    print("Tuning stats:")
    print(json.dumps(best_stats, indent=2))
    if args.update_model:
        print(f"Updated model thresholds in: {args.model}")


if __name__ == "__main__":
    main()
