#!/usr/bin/env python3
import argparse
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


REQUIRED_COLUMNS = [
    "date",
    "ticker",
    "close",
    "volume",
    "market_return_1d",
    "sector_return_1d",
    "sentiment_score",
    "pe_ratio",
    "pb_ratio",
    "debt_to_equity",
    "revenue_growth_qoq",
    "eps_growth_qoq",
    "volatility_20d",
    "target_forward_return_5d",
]

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train MarketMind baseline model.")
    parser.add_argument("--input", required=True, help="Path to training CSV")
    parser.add_argument(
        "--model-out",
        default="marketmind_model.joblib",
        help="Output path for trained model artifact",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Fraction of latest rows used for test set (time-based split)",
    )
    return parser.parse_args()


def validate_columns(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data["date"] = pd.to_datetime(data["date"])
    data = data.sort_values(["ticker", "date"]).reset_index(drop=True)

    data["price_return_1d"] = data.groupby("ticker")["close"].pct_change()
    data["volume_change_1d"] = data.groupby("ticker")["volume"].pct_change()
    data["sentiment_x_market"] = data["sentiment_score"] * data["market_return_1d"]
    data["growth_blend"] = 0.6 * data["revenue_growth_qoq"] + 0.4 * data["eps_growth_qoq"]
    data["valuation_pressure"] = data["pe_ratio"] * data["pb_ratio"]

    return data


def time_split(df: pd.DataFrame, test_size: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    ordered = df.sort_values("date").reset_index(drop=True)
    split_idx = int(len(ordered) * (1 - test_size))
    split_idx = max(1, min(split_idx, len(ordered) - 1))
    return ordered.iloc[:split_idx].copy(), ordered.iloc[split_idx:].copy()


def directional_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.sign(y_true) == np.sign(y_pred)))


def build_pipeline(numeric_features: list[str]) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_features,
            )
        ]
    )
    model = RandomForestRegressor(
        n_estimators=350,
        min_samples_leaf=8,
        random_state=42,
        n_jobs=-1,
    )
    return Pipeline(steps=[("prep", preprocessor), ("model", model)])


def main() -> None:
    args = parse_args()
    raw = pd.read_csv(args.input)
    validate_columns(raw)

    data = engineer_features(raw).dropna(subset=["target_forward_return_5d"]).copy()

    candidate_feature_columns = [
        "close",
        "volume",
        "market_return_1d",
        "sector_return_1d",
        "global_return_1d",
        "dollar_index_return_1d",
        "oil_return_1d",
        "vix_level",
        "interest_rate_10y",
        "inflation_yoy",
        "fed_funds_rate",
        "sentiment_score",
        "breaking_news_count",
        "announcement_count",
        "policy_impact_score",
        "rumor_confirmed_ratio",
        "pe_ratio",
        "pb_ratio",
        "debt_to_equity",
        "revenue_growth_qoq",
        "eps_growth_qoq",
        "operating_cashflow",
        "free_cashflow",
        "gross_margins",
        "cash_to_debt",
        "days_to_next_earnings",
        "volatility_20d",
        "market_depth_proxy",
        "bid_ask_spread_pct",
        "breakout_20d",
        "breakdown_20d",
        "ma_20",
        "ma_50",
        "ma_200",
        "rsi_14",
        "macd",
        "macd_signal",
        "macd_hist",
        "support_20d",
        "resistance_20d",
        "near_support",
        "near_resistance",
        "trend_reversal_flag",
        "volume_spike_ratio",
        "price_return_1d",
        "volume_change_1d",
        "sentiment_x_market",
        "growth_blend",
        "valuation_pressure",
    ]
    feature_columns = [c for c in candidate_feature_columns if c in data.columns]
    if len(feature_columns) < 8:
        raise ValueError("Not enough usable feature columns found for training.")

    train_df, test_df = time_split(data, args.test_size)

    x_train = train_df[feature_columns]
    y_train = train_df["target_forward_return_5d"]
    x_test = test_df[feature_columns]
    y_test = test_df["target_forward_return_5d"]

    pipeline = build_pipeline(feature_columns)
    pipeline.fit(x_train, y_train)
    preds = pipeline.predict(x_test)

    rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
    metrics = {
        "mae": float(mean_absolute_error(y_test, preds)),
        "rmse": rmse,
        "r2": float(r2_score(y_test, preds)),
        "directional_accuracy": directional_accuracy(y_test.values, preds),
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
    }

    signal_thresholds = {
        "enter_pred_return": 0.015,
        "exit_pred_return": -0.01,
        "high_risk_volatility": 0.05,
    }

    bundle = {
        "pipeline": pipeline,
        "feature_columns": feature_columns,
        "target_column": "target_forward_return_5d",
        "signal_thresholds": signal_thresholds,
    }
    joblib.dump(bundle, args.model_out)

    print("Training complete.")
    print(f"Model saved to: {args.model_out}")
    print("Metrics:")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
