#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

TICKERS="${MARKETMIND_TICKERS:-AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA}"
PERIOD="${MARKETMIND_PERIOD:-6mo}"
NEWS_PROVIDER="${MARKETMIND_NEWS_PROVIDER:-none}"
CAPITAL="${MARKETMIND_CAPITAL:-100000}"
RISK_BUDGET="${MARKETMIND_RISK_BUDGET:-0.8}"
TOP_N="${MARKETMIND_TOP_N:-8}"
MAX_WEIGHT="${MARKETMIND_MAX_POSITION_WEIGHT:-0.25}"
ALERTS="${MARKETMIND_ALERTS:-auto}"
ALERT_TOP_N="${MARKETMIND_ALERT_TOP_N:-5}"

python marketmind_ml/fetch_live_data.py \
  --tickers "$TICKERS" \
  --period "$PERIOD" \
  --news-provider "$NEWS_PROVIDER" \
  --output marketmind_ml/live_market_data.csv

python marketmind_ml/predict_signal.py \
  --model marketmind_ml/model.joblib \
  --input marketmind_ml/live_market_data.csv \
  --latest-only \
  --output marketmind_signals.csv

python marketmind_ml/rank_portfolio.py \
  --signals marketmind_signals.csv \
  --output marketmind_portfolio_plan.csv \
  --report-output marketmind_portfolio_report.md \
  --capital "$CAPITAL" \
  --risk-budget "$RISK_BUDGET" \
  --top-n "$TOP_N" \
  --max-position-weight "$MAX_WEIGHT"

python marketmind_ml/build_intelligence_report.py \
  --live-data marketmind_ml/live_market_data.csv \
  --signals marketmind_signals.csv \
  --portfolio marketmind_portfolio_plan.csv \
  --output marketmind_intelligence_report.md

python marketmind_ml/send_alerts.py \
  --portfolio marketmind_portfolio_plan.csv \
  --top-n "$ALERT_TOP_N" \
  --channel "$ALERTS"

echo "MarketMind daily run completed."
