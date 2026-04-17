import yfinance as yf
import pandas as pd
from typing import Optional
import datetime
import io
import json
import pathlib
import requests

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

_CACHE_DIR = pathlib.Path(__file__).parent.parent / "cache"
_NSE_CSV_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
_BSE_API_URL = (
    "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
    "?Group=&Scripcode=&industry=&segment=Equity&status=Active"
)
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; stock-agent/1.0)"}


def fetch_universe(refresh: bool = False) -> list:
    """Return all NSE+BSE equity tickers with daily caching.

    NSE tickers are bare symbols (e.g. 'RELIANCE').
    BSE-only tickers include exchange suffix (e.g. '543217.BO').
    Pass refresh=True to ignore the cache and re-fetch.
    """
    _CACHE_DIR.mkdir(exist_ok=True)
    universe_cache = _CACHE_DIR / "universe.json"
    if not refresh and universe_cache.exists():
        try:
            data = json.loads(universe_cache.read_text())
            age = datetime.datetime.utcnow() - datetime.datetime.fromisoformat(data["fetched_at"])
            if age < datetime.timedelta(hours=24):
                return data["tickers"]
        except Exception:
            pass

    tickers = _fetch_nse_bse_tickers()
    if tickers:
        try:
            universe_cache.write_text(json.dumps({
                "tickers": tickers,
                "fetched_at": datetime.datetime.utcnow().isoformat(),
            }))
        except Exception as e:
            print(f"Warning: could not write universe cache: {e}")
        return tickers

    print("Warning: could not fetch NSE/BSE universe. Using built-in fallback list.")
    return list(NSE_UNIVERSE)


def _fetch_nse_bse_tickers() -> list:
    nse = _fetch_nse_symbols()
    bse = _fetch_bse_tickers(exclude=set(nse))
    return nse + bse


def _fetch_nse_symbols() -> list:
    try:
        resp = requests.get(_NSE_CSV_URL, headers=_HEADERS, timeout=30)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        return df["SYMBOL"].dropna().str.strip().tolist()
    except Exception:
        return []


def _fetch_bse_tickers(exclude: set) -> list:
    try:
        resp = requests.get(_BSE_API_URL, headers=_HEADERS, timeout=30)
        resp.raise_for_status()
        rows = resp.json()
        if isinstance(rows, dict):
            rows = rows.get("Table", [])
        tickers = []
        for item in rows:
            scrip_id = str(item.get("scrip_id", "")).strip().upper()
            if scrip_id and scrip_id not in exclude:
                tickers.append(f"{scrip_id}.BO")
        return tickers
    except Exception:
        return []


def get_stock_data(ticker: str) -> Optional[dict]:
    """Fetch fundamental and technical data for a single NSE or BSE stock."""
    symbol = ticker if "." in ticker else f"{ticker}.NS"
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        hist = stock.history(period="1y")

        if hist.empty or not info:
            return None

        if len(hist) < 200:
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
    gain = delta.clip(lower=0).ewm(com=period - 1, min_periods=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=period - 1, min_periods=period, adjust=False).mean()
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
