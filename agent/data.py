import yfinance as yf
import pandas as pd
from typing import Optional

NSE_UNIVERSE = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "KOTAKBANK", "LT", "AXISBANK",
    "BAJFINANCE", "BHARTIARTL", "ASIANPAINT", "MARUTI", "HCLTECH",
    "WIPRO", "ULTRACEMCO", "SUNPHARMA", "TATAMOTORS", "SBIN",
    "DRREDDY", "CIPLA", "EICHERMOT", "HEROMOTOCO", "JSWSTEEL",
    "TATASTEEL", "TECHM", "APOLLOHOSP", "TITAN", "NESTLEIND",
    "NTPC", "POWERGRID", "ONGC", "COALINDIA", "BPCL",
    "ADANIPORTS", "DIVISLAB", "BAJAJ-AUTO", "BRITANNIA", "PIDILITIND",
    "GRASIM", "INDUSINDBK", "M&M", "TATACONSUM", "SHREECEM",
]


def get_stock_data(ticker: str) -> Optional[dict]:
    """Fetch fundamental and technical data for a single NSE stock."""
    symbol = f"{ticker}.NS"
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        hist = stock.history(period="1y")

        if hist.empty or not info:
            return None

        close = hist["Close"]
        rsi = _calculate_rsi(close)
        ma50 = float(close.rolling(50).mean().iloc[-1])
        ma200 = float(close.rolling(200).mean().iloc[-1])
        macd, signal = _calculate_macd(close)

        return {
            "ticker": ticker,
            "name": info.get("longName", ticker),
            "sector": info.get("sector", "Unknown"),
            "price": info.get("currentPrice") or float(close.iloc[-1]),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "eps": info.get("trailingEps"),
            "dividend_yield": (info.get("dividendYield") or 0) * 100,
            "debt_to_equity": info.get("debtToEquity"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "volume": info.get("averageVolume"),
            "rsi": rsi,
            "ma50": ma50,
            "ma200": ma200,
            "macd_bullish": macd > signal,
        }
    except Exception:
        return None


def _calculate_rsi(close: pd.Series, period: int = 14) -> float:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 2)


def _calculate_macd(close: pd.Series):
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return float(macd.iloc[-1]), float(signal.iloc[-1])


def get_multiple_stocks(tickers: list) -> list:
    """Fetch data for multiple stocks, silently skipping failures."""
    results = []
    for ticker in tickers:
        data = get_stock_data(ticker)
        if data:
            results.append(data)
    return results
