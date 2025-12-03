"""
Fetch market caps via yfinance and build companies.csv with popularity scores.

Input: tickers.csv (columns: company_name,ticker)
Output: companies.csv (columns: company_name,ticker,market_cap,popularity_score)
"""

import csv
import math
import sys
from pathlib import Path

import yfinance as yf


def fetch_market_cap(ticker: str) -> int:
    """Return market cap for ticker, or 0 on error/missing."""
    try:
        info = yf.Ticker(ticker).info
        cap = info.get("marketCap")
        if cap is None:
            print(f"Warning: marketCap missing for {ticker}", file=sys.stderr)
            return 0
        return int(cap)
    except Exception as exc:  # network or lookup failures
        print(f"Error fetching {ticker}: {exc}", file=sys.stderr)
        return 0


def main():
    tickers_path = Path("tickers.csv")
    if not tickers_path.exists():
        print("tickers.csv not found in current directory.", file=sys.stderr)
        sys.exit(1)

    rows = []
    with tickers_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "company_name" not in reader.fieldnames or "ticker" not in reader.fieldnames:
            print("tickers.csv must have columns: company_name,ticker", file=sys.stderr)
            sys.exit(1)
        for row in reader:
            company = row.get("company_name", "").strip()
            ticker = row.get("ticker", "").strip()
            if not company or not ticker:
                continue
            cap = fetch_market_cap(ticker)
            popularity_score = cap  # direct proxy
            rows.append(
                {
                    "company_name": company,
                    "ticker": ticker,
                    "market_cap": cap,
                    "popularity_score": popularity_score,
                }
            )

    out_path = Path("companies.csv")
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["company_name", "ticker", "market_cap", "popularity_score"]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
