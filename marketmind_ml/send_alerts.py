#!/usr/bin/env python3
import argparse
import os

import pandas as pd
import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send MarketMind alerts to Slack and/or Telegram.")
    parser.add_argument(
        "--portfolio",
        default="marketmind_portfolio_plan.csv",
        help="Portfolio plan CSV path",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="How many top positions to include",
    )
    parser.add_argument(
        "--channel",
        choices=["auto", "none", "slack", "telegram", "both"],
        default="auto",
        help="Where to send notifications",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when configured provider send fails",
    )
    return parser.parse_args()


def build_message(df: pd.DataFrame, top_n: int) -> str:
    header = "MarketMind Daily Update"
    if df.empty:
        return f"{header}\nNo actionable ranked positions today."

    picks = df.sort_values("rank").head(top_n)
    lines = [header, "Top ranked positions:"]
    for _, row in picks.iterrows():
        lines.append(
            f"{int(row['rank'])}. {row['ticker']} | {row['action']} | "
            f"Pred5D {row['pred_forward_return_5d']:.2%} | Vol {row['volatility_20d']:.2%} | "
            f"Wt {row['allocation_weight']:.2%} | ${row['allocated_capital_usd']:,.0f}"
        )
    return "\n".join(lines)


def send_slack(text: str) -> tuple[bool, str]:
    webhook = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if not webhook:
        return False, "SLACK_WEBHOOK_URL missing"
    try:
        response = requests.post(webhook, json={"text": text}, timeout=15)
        if 200 <= response.status_code < 300:
            return True, "sent"
        return False, f"status={response.status_code}"
    except requests.RequestException as exc:
        return False, str(exc)


def send_telegram(text: str) -> tuple[bool, str]:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return False, "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing"
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        response = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=15)
        if 200 <= response.status_code < 300:
            return True, "sent"
        return False, f"status={response.status_code}"
    except requests.RequestException as exc:
        return False, str(exc)


def main() -> None:
    args = parse_args()
    plan = pd.read_csv(args.portfolio)
    message = build_message(plan, args.top_n)

    if args.channel == "none":
        print("Notifications disabled (--channel none).")
        return

    wants_slack = args.channel in {"auto", "slack", "both"}
    wants_telegram = args.channel in {"auto", "telegram", "both"}

    failures = []
    sent = []

    if wants_slack:
        ok, detail = send_slack(message)
        if ok:
            sent.append("slack")
        elif args.channel in {"slack", "both"} or (args.channel == "auto" and os.getenv("SLACK_WEBHOOK_URL")):
            failures.append(f"Slack: {detail}")

    if wants_telegram:
        ok, detail = send_telegram(message)
        if ok:
            sent.append("telegram")
        elif args.channel in {"telegram", "both"} or (
            args.channel == "auto" and os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID")
        ):
            failures.append(f"Telegram: {detail}")

    if sent:
        print(f"Alert sent via: {', '.join(sent)}")
    else:
        print("No alert sent (no configured channels available).")

    if failures:
        print("Send failures:")
        for f in failures:
            print(f"- {f}")
        if args.strict:
            raise RuntimeError("One or more alert sends failed.")


if __name__ == "__main__":
    main()
