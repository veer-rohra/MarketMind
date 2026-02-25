# MarketMind ML Baseline

This is a practical baseline ML pipeline for the MarketMind vision.

It does three things:

1. Trains a model to predict forward 5-day return.
2. Estimates risk using realized volatility.
3. Converts predictions into actions: `ENTER`, `EXIT`, `WAIT`, `AVOID`.

## Quick start

```bash
cd /Users/veer/Documents/New\ project
python3 -m venv .venv
source .venv/bin/activate
pip install -r marketmind_ml/requirements.txt
python marketmind_ml/generate_synthetic_data.py --rows 2500 --output marketmind_ml/sample_market_data.csv
python marketmind_ml/train_marketmind.py --input marketmind_ml/sample_market_data.csv --model-out marketmind_ml/model.joblib
python marketmind_ml/predict_signal.py --model marketmind_ml/model.joblib --input marketmind_ml/sample_market_data.csv --latest-only
```

## Live data workflow

Train once (already done in your session), then run with live symbols:

```bash
source .venv/bin/activate
python marketmind_ml/fetch_live_data.py --tickers AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA --period 6mo --news-provider none --output marketmind_ml/live_market_data.csv
python marketmind_ml/predict_signal.py --model marketmind_ml/model.joblib --input marketmind_ml/live_market_data.csv --latest-only
python marketmind_ml/rank_portfolio.py --signals marketmind_signals.csv --capital 100000 --risk-budget 0.8
python marketmind_ml/build_intelligence_report.py --live-data marketmind_ml/live_market_data.csv --signals marketmind_signals.csv --portfolio marketmind_portfolio_plan.csv --output marketmind_intelligence_report.md
```

Optional sentiment providers:

- `--news-provider newsapi` with `NEWSAPI_KEY` env var
- `--news-provider finnhub` with `FINNHUB_API_KEY` env var
- Optional macro data from FRED with `FRED_API_KEY` env var

Example:

```bash
export NEWSAPI_KEY=your_key_here
python marketmind_ml/fetch_live_data.py --tickers AAPL,MSFT,NVDA --news-provider newsapi
```

## Portfolio ranking and allocation

`rank_portfolio.py` ranks candidates by risk-adjusted expected return and allocates capital with a per-position cap.

Outputs:

- `marketmind_portfolio_plan.csv`
- `marketmind_portfolio_report.md`

Example:

```bash
python marketmind_ml/rank_portfolio.py \
  --signals marketmind_signals.csv \
  --output marketmind_portfolio_plan.csv \
  --report-output marketmind_portfolio_report.md \
  --capital 150000 \
  --risk-budget 0.75 \
  --top-n 10 \
  --max-position-weight 0.20
```

## Daily scheduler

### Local cron

```bash
chmod +x marketmind_ml/run_daily.sh
crontab -e
```

Add:

```cron
35 9 * * 1-5 /bin/bash /Users/veer/Documents/New\ project/marketmind_ml/run_daily.sh >> /Users/veer/Documents/New\ project/marketmind_ml/daily.log 2>&1
```

### GitHub Actions

Workflow file:

- `.github/workflows/marketmind_daily.yml`

Default run time:

- Weekdays at 13:35 UTC (adjust `cron` as needed)

Optional repo settings:

- Secrets: `NEWSAPI_KEY`, `FINNHUB_API_KEY`, `FRED_API_KEY`, `SLACK_WEBHOOK_URL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- Variables: `MARKETMIND_TICKERS`, `MARKETMIND_PERIOD`, `MARKETMIND_NEWS_PROVIDER`, `MARKETMIND_CAPITAL`, `MARKETMIND_RISK_BUDGET`, `MARKETMIND_TOP_N`, `MARKETMIND_MAX_POSITION_WEIGHT`, `MARKETMIND_ALERTS`, `MARKETMIND_ALERT_TOP_N`

## Threshold tuning

Tune thresholds on historical labeled data so you get a healthier action distribution:

```bash
python marketmind_ml/tune_thresholds.py \
  --model marketmind_ml/model.joblib \
  --input marketmind_ml/sample_market_data.csv \
  --target-enter-rate 0.25 \
  --output-thresholds marketmind_ml/tuned_thresholds.json \
  --update-model
```

Use tuned thresholds at inference time (if you do not use `--update-model`):

```bash
python marketmind_ml/predict_signal.py \
  --model marketmind_ml/model.joblib \
  --input marketmind_ml/live_market_data.csv \
  --latest-only \
  --thresholds-file marketmind_ml/tuned_thresholds.json
```

You can also override directly:

```bash
python marketmind_ml/predict_signal.py \
  --model marketmind_ml/model.joblib \
  --input marketmind_ml/live_market_data.csv \
  --latest-only \
  --enter-threshold 0.012 \
  --exit-threshold -0.008 \
  --risk-threshold 0.055
```

## Slack and Telegram alerts

Send alerts manually:

```bash
export SLACK_WEBHOOK_URL=...
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...
python marketmind_ml/send_alerts.py --portfolio marketmind_portfolio_plan.csv --channel auto --top-n 5
```

`run_daily.sh` already calls alerts and supports:

- `MARKETMIND_ALERTS` = `auto|none|slack|telegram|both`
- `MARKETMIND_ALERT_TOP_N` = number of rows in alert

## Intelligence report

Each daily run also creates:

- `marketmind_intelligence_report.md`

The report is structured by your A/B/C/D/E framework for each ticker:

- A. Real-time market data
- B. Technical indicators
- C. Fundamental data
- D. News and sentiment
- E. Macro environment

## Expected input schema

CSV columns:

- `date` (YYYY-MM-DD)
- `ticker`
- `close`
- `volume`
- `market_return_1d`
- `sector_return_1d`
- `sentiment_score` (roughly -1 to 1)
- `pe_ratio`
- `pb_ratio`
- `debt_to_equity`
- `revenue_growth_qoq`
- `eps_growth_qoq`
- `volatility_20d`
- `target_forward_return_5d` (training target)

The included synthetic generator produces this schema.

Live ingestion includes additional fields such as: volume spikes, market-depth proxy, breakout/breakdown flags, moving averages, RSI, MACD, support/resistance, trend reversal flag, cashflow metrics, rumor-vs-confirmed ratio, and macro proxies (rates, VIX, global, dollar, oil, inflation/fed funds when available).

## How decisions are made

The model predicts forward return, then applies rule thresholds:

- `ENTER`: prediction is high and risk is acceptable
- `WAIT`: prediction is positive but weak/uncertain
- `EXIT`: prediction is negative with moderate risk
- `AVOID`: prediction is strongly negative or risk is high

This is intentionally a baseline and should be upgraded with your real data feeds.
