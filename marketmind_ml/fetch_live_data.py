#!/usr/bin/env python3
import argparse
import os
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import requests
import yfinance as yf

SECTOR_ETF_MAP = {
    "Technology": "XLK",
    "Communication Services": "XLC",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Healthcare": "XLV",
    "Financial Services": "XLF",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Basic Materials": "XLB",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
}

POS_WORDS = {
    "beat", "beats", "growth", "surge", "strong", "bullish", "upgrade", "expands", "record", "profit",
    "outperform", "raised", "buyback", "optimistic", "momentum", "win",
}
NEG_WORDS = {
    "miss", "falls", "drop", "weak", "bearish", "downgrade", "lawsuit", "probe", "loss", "cut",
    "warning", "decline", "slump", "risk", "headwind", "delay",
}
RUMOR_WORDS = {"rumor", "rumour", "unconfirmed", "speculation", "reportedly"}
CONFIRMED_WORDS = {"confirmed", "official", "files", "announces", "announced", "reported"}
BREAKING_WORDS = {"breaking", "urgent", "just in", "flash"}
ANNOUNCEMENT_WORDS = {"announces", "launches", "partnership", "agreement", "guidance", "earnings"}
POLICY_WORDS = {"fed", "regulation", "policy", "tariff", "ban", "rate", "inflation", "government", "sec"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch live market/fundamental/sentiment data into MarketMind schema.")
    parser.add_argument("--tickers", required=True, help="Comma-separated tickers, e.g. AAPL,MSFT,NVDA")
    parser.add_argument("--period", default="1y", help="Yahoo period for history (e.g. 3mo, 6mo, 1y)")
    parser.add_argument("--interval", default="1d", help="Yahoo interval, default 1d")
    parser.add_argument(
        "--news-provider",
        choices=["none", "newsapi", "finnhub"],
        default="none",
        help="Optional news provider for sentiment",
    )
    parser.add_argument("--output", default="marketmind_ml/live_market_data.csv", help="Output CSV path")
    return parser.parse_args()


def safe_float(value: object, default: float = np.nan) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / (loss.replace(0, np.nan))
    return 100 - (100 / (1 + rs))


def normalize_dates(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True).dt.tz_convert(None).dt.normalize()


def fetch_newsapi_headlines(ticker: str) -> list[str]:
    api_key = os.getenv("NEWSAPI_KEY")
    if not api_key:
        return []

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": ticker,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 50,
        "apiKey": api_key,
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        payload = response.json()
        return [a.get("title", "") for a in payload.get("articles", []) if a.get("title")]
    except requests.RequestException:
        return []


def fetch_finnhub_headlines(ticker: str) -> list[str]:
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return []

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    from_date = (datetime.now(UTC) - pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    url = "https://finnhub.io/api/v1/company-news"
    params = {
        "symbol": ticker,
        "from": from_date,
        "to": today,
        "token": api_key,
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        payload = response.json()
        return [a.get("headline", "") for a in payload if a.get("headline")]
    except requests.RequestException:
        return []


def count_keyword_hits(texts: list[str], keywords: set[str]) -> int:
    count = 0
    for text in texts:
        lower = text.lower()
        for k in keywords:
            if k in lower:
                count += 1
                break
    return count


def analyze_headlines(headlines: list[str]) -> dict[str, float]:
    if not headlines:
        return {
            "sentiment_score": 0.0,
            "breaking_news_count": 0.0,
            "announcement_count": 0.0,
            "policy_impact_score": 0.0,
            "rumor_count": 0.0,
            "confirmed_count": 0.0,
            "rumor_confirmed_ratio": 0.0,
            "headline_count": 0.0,
        }

    score = 0
    token_count = 0
    for text in headlines:
        for token in text.lower().split():
            cleaned = "".join(ch for ch in token if ch.isalpha())
            if not cleaned:
                continue
            token_count += 1
            if cleaned in POS_WORDS:
                score += 1
            elif cleaned in NEG_WORDS:
                score -= 1

    sentiment = float(np.clip(score / max(token_count, 20), -1, 1))
    rumor_count = float(count_keyword_hits(headlines, RUMOR_WORDS))
    confirmed_count = float(count_keyword_hits(headlines, CONFIRMED_WORDS))

    return {
        "sentiment_score": sentiment,
        "breaking_news_count": float(count_keyword_hits(headlines, BREAKING_WORDS)),
        "announcement_count": float(count_keyword_hits(headlines, ANNOUNCEMENT_WORDS)),
        "policy_impact_score": float(count_keyword_hits(headlines, POLICY_WORDS)),
        "rumor_count": rumor_count,
        "confirmed_count": confirmed_count,
        "rumor_confirmed_ratio": float(rumor_count / max(confirmed_count, 1.0)),
        "headline_count": float(len(headlines)),
    }


def fetch_news_features(ticker: str, provider: str) -> dict[str, float]:
    if provider == "newsapi":
        headlines = fetch_newsapi_headlines(ticker)
    elif provider == "finnhub":
        headlines = fetch_finnhub_headlines(ticker)
    else:
        headlines = []
    return analyze_headlines(headlines)


def get_ticker_info(ticker: yf.Ticker) -> dict:
    try:
        info = ticker.info
        return info if isinstance(info, dict) else {}
    except Exception:
        return {}


def fetch_symbol_series(symbol: str, period: str, interval: str, field: str = "Close") -> pd.Series:
    hist = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=False)
    if hist.empty or field not in hist.columns:
        return pd.Series(dtype=float)
    out = hist[field].copy()
    out.index = normalize_dates(out.index.to_series())
    return out


def fetch_fred_latest(series_id: str) -> float:
    api_key = os.getenv("FRED_API_KEY", "").strip()
    if not api_key:
        return np.nan

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {"series_id": series_id, "api_key": api_key, "file_type": "json", "sort_order": "desc", "limit": 2}
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        observations = response.json().get("observations", [])
        for row in observations:
            value = row.get("value", ".")
            if value not in {".", None, ""}:
                return safe_float(value, np.nan)
        return np.nan
    except requests.RequestException:
        return np.nan


def compute_macro_inputs(period: str, interval: str) -> dict[str, object]:
    spy_close = fetch_symbol_series("SPY", period, interval)
    acwi_close = fetch_symbol_series("ACWI", period, interval)
    dxy_close = fetch_symbol_series("DX-Y.NYB", period, interval)
    oil_close = fetch_symbol_series("CL=F", period, interval)
    vix_close = fetch_symbol_series("^VIX", period, interval)
    tnx_close = fetch_symbol_series("^TNX", period, interval)

    return {
        "market_return_1d": spy_close.pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0),
        "global_return_1d": acwi_close.pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0),
        "dollar_index_return_1d": dxy_close.pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0),
        "oil_return_1d": oil_close.pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0),
        "vix_level": vix_close,
        "interest_rate_10y": tnx_close / 100.0,
        "inflation_yoy": fetch_fred_latest("CPIAUCSL"),
        "fed_funds_rate": fetch_fred_latest("FEDFUNDS"),
    }


def align_by_date(date_series: pd.Series, source: pd.Series, default: float = 0.0) -> pd.Series:
    if source.empty:
        return pd.Series(default, index=date_series.index, dtype=float)
    return date_series.map(source).astype(float).fillna(default)


def build_rows_for_ticker(symbol: str, period: str, interval: str, provider: str, macro: dict[str, object]) -> pd.DataFrame:
    tk = yf.Ticker(symbol)
    hist = tk.history(period=period, interval=interval, auto_adjust=False)
    if hist.empty:
        return pd.DataFrame()

    hist = hist.reset_index().rename(columns={"Date": "date", "Close": "close", "Volume": "volume"})
    hist["date"] = normalize_dates(hist["date"])
    hist = hist.sort_values("date").reset_index(drop=True)

    info = get_ticker_info(tk)
    sector = info.get("sector", "")
    sector_etf = SECTOR_ETF_MAP.get(sector, "")
    sector_close = fetch_symbol_series(sector_etf, period, interval) if sector_etf else pd.Series(dtype=float)
    sector_return_1d = sector_close.pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0)

    close_series = hist["close"].astype(float)
    volume_series = hist["volume"].astype(float)

    hist["ticker"] = symbol

    # A) Real-time market behavior
    hist["price_return_1d"] = close_series.pct_change()
    hist["volume_change_1d"] = volume_series.pct_change()
    hist["avg_volume_20d"] = volume_series.rolling(20).mean()
    hist["volume_spike_ratio"] = volume_series / hist["avg_volume_20d"].replace(0, np.nan)
    hist["volatility_20d"] = close_series.pct_change().rolling(20).std()
    hist["support_20d"] = close_series.rolling(20).min()
    hist["resistance_20d"] = close_series.rolling(20).max()
    hist["breakout_20d"] = (close_series > hist["resistance_20d"].shift(1)).astype(int)
    hist["breakdown_20d"] = (close_series < hist["support_20d"].shift(1)).astype(int)

    bid = safe_float(info.get("bid", np.nan))
    ask = safe_float(info.get("ask", np.nan))
    bid_size = safe_float(info.get("bidSize", 0.0), 0.0)
    ask_size = safe_float(info.get("askSize", 0.0), 0.0)
    market_depth_proxy = bid_size + ask_size
    spread_pct = ((ask - bid) / close_series.replace(0, np.nan)).fillna(0.0) if not np.isnan(bid + ask) else 0.0
    hist["market_depth_proxy"] = market_depth_proxy
    hist["bid_ask_spread_pct"] = spread_pct

    # B) Technical indicators
    hist["ma_20"] = close_series.rolling(20).mean()
    hist["ma_50"] = close_series.rolling(50).mean()
    hist["ma_200"] = close_series.rolling(200).mean()
    hist["rsi_14"] = rsi(close_series, 14)
    hist["macd"] = ema(close_series, 12) - ema(close_series, 26)
    hist["macd_signal"] = ema(hist["macd"], 9)
    hist["macd_hist"] = hist["macd"] - hist["macd_signal"]
    hist["trend_reversal_flag"] = ((hist["macd_hist"] * hist["macd_hist"].shift(1)) < 0).astype(int)
    hist["near_support"] = ((close_series - hist["support_20d"]).abs() / close_series.replace(0, np.nan) <= 0.01).astype(int)
    hist["near_resistance"] = ((close_series - hist["resistance_20d"]).abs() / close_series.replace(0, np.nan) <= 0.01).astype(int)

    # C) Fundamentals
    hist["pe_ratio"] = safe_float(info.get("trailingPE", info.get("forwardPE", np.nan)))
    hist["pb_ratio"] = safe_float(info.get("priceToBook", np.nan))
    hist["debt_to_equity"] = safe_float(info.get("debtToEquity", 0.0), 0.0)
    hist["revenue_growth_qoq"] = safe_float(info.get("revenueGrowth", 0.0), 0.0)
    hist["eps_growth_qoq"] = safe_float(info.get("earningsQuarterlyGrowth", 0.0), 0.0)
    hist["operating_cashflow"] = safe_float(info.get("operatingCashflow", np.nan))
    hist["free_cashflow"] = safe_float(info.get("freeCashflow", np.nan))
    hist["gross_margins"] = safe_float(info.get("grossMargins", np.nan))
    total_cash = safe_float(info.get("totalCash", np.nan))
    total_debt = safe_float(info.get("totalDebt", np.nan))
    hist["cash_to_debt"] = float(total_cash / (abs(total_debt) + 1e-9)) if not np.isnan(total_cash) else np.nan

    earnings_ts = info.get("earningsTimestamp") or info.get("earningsTimestampStart")
    if earnings_ts:
        earnings_date = pd.to_datetime(earnings_ts, unit="s", utc=True).tz_convert(None).normalize()
        hist["days_to_next_earnings"] = (earnings_date - hist["date"]).dt.days
    else:
        hist["days_to_next_earnings"] = np.nan

    # D) News and sentiment
    news = fetch_news_features(symbol, provider)
    for key, value in news.items():
        hist[key] = value

    # E) Macro environment
    hist["market_return_1d"] = align_by_date(hist["date"], macro["market_return_1d"], default=0.0)
    hist["sector_return_1d"] = align_by_date(hist["date"], sector_return_1d, default=hist["market_return_1d"].mean())
    hist["global_return_1d"] = align_by_date(hist["date"], macro["global_return_1d"], default=0.0)
    hist["dollar_index_return_1d"] = align_by_date(hist["date"], macro["dollar_index_return_1d"], default=0.0)
    hist["oil_return_1d"] = align_by_date(hist["date"], macro["oil_return_1d"], default=0.0)
    hist["vix_level"] = align_by_date(hist["date"], macro["vix_level"], default=np.nan)
    hist["interest_rate_10y"] = align_by_date(hist["date"], macro["interest_rate_10y"], default=np.nan)
    hist["inflation_yoy"] = macro["inflation_yoy"]
    hist["fed_funds_rate"] = macro["fed_funds_rate"]

    # Placeholder target column for inference datasets.
    hist["target_forward_return_5d"] = np.nan

    hist["date"] = hist["date"].dt.strftime("%Y-%m-%d")

    cols = [
        "date",
        "ticker",
        "close",
        "volume",
        "price_return_1d",
        "volume_change_1d",
        "avg_volume_20d",
        "volume_spike_ratio",
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
        "rumor_count",
        "confirmed_count",
        "rumor_confirmed_ratio",
        "headline_count",
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
        "target_forward_return_5d",
    ]
    return hist[cols]


def main() -> None:
    args = parse_args()
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    if not tickers:
        raise ValueError("No valid tickers supplied")

    macro = compute_macro_inputs(args.period, args.interval)

    frames = []
    for t in tickers:
        frame = build_rows_for_ticker(t, args.period, args.interval, args.news_provider, macro)
        if not frame.empty:
            frames.append(frame)

    if not frames:
        raise RuntimeError("No ticker data was fetched. Check symbols and network/API availability.")

    out = pd.concat(frames, ignore_index=True).sort_values(["date", "ticker"]).reset_index(drop=True)
    out.to_csv(args.output, index=False)

    print(f"Saved live dataset to: {args.output}")
    print(f"Rows: {len(out)} | Tickers: {','.join(sorted(set(out['ticker'])))}")
    print(out.tail(10).to_string(index=False))


if __name__ == "__main__":
    main()
