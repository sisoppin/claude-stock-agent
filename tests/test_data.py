import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from agent.data import (
    get_stock_data, _calculate_rsi, _calculate_macd,
    get_multiple_stocks, NSE_UNIVERSE, fetch_universe,
)


def _make_hist():
    dates = pd.date_range("2024-01-01", periods=250)
    prices = pd.Series(np.linspace(1000, 1500, 250), index=dates)
    return pd.DataFrame({
        "Close": prices,
        "Open": prices * 0.99,
        "High": prices * 1.01,
        "Low": prices * 0.98,
        "Volume": [1_000_000] * 250,
    })


def _make_info():
    return {
        "longName": "Reliance Industries",
        "sector": "Energy",
        "currentPrice": 2800.50,
        "marketCap": 1_890_000_000_000,
        "trailingPE": 12.5,
        "trailingEps": 224.0,
        "dividendYield": 0.005,
        "debtToEquity": 35.2,
        "fiftyTwoWeekHigh": 3024.0,
        "fiftyTwoWeekLow": 2180.0,
        "averageVolume": 5_000_000,
    }


@patch("agent.data.yf.Ticker")
def test_get_stock_data_returns_dict(mock_ticker):
    mock_t = MagicMock()
    mock_t.info = _make_info()
    mock_t.history.return_value = _make_hist()
    mock_ticker.return_value = mock_t

    result = get_stock_data("RELIANCE")

    assert result is not None
    assert result["ticker"] == "RELIANCE"
    assert result["price"] == 2800.50
    assert result["pe_ratio"] == 12.5
    assert result["sector"] == "Energy"
    assert 0 <= result["rsi"] <= 100
    assert isinstance(result["macd_bullish"], bool)


@patch("agent.data.yf.Ticker")
def test_get_stock_data_returns_none_on_empty_hist(mock_ticker):
    mock_t = MagicMock()
    mock_t.info = _make_info()
    mock_t.history.return_value = pd.DataFrame()
    mock_ticker.return_value = mock_t

    result = get_stock_data("BADTICKER")
    assert result is None


@patch("agent.data.yf.Ticker")
def test_get_stock_data_appends_ns_suffix(mock_ticker):
    mock_t = MagicMock()
    mock_t.info = _make_info()
    mock_t.history.return_value = _make_hist()
    mock_ticker.return_value = mock_t

    get_stock_data("RELIANCE")
    mock_ticker.assert_called_once_with("RELIANCE.NS")


def test_calculate_rsi_returns_value_between_0_and_100():
    prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
                        111, 110, 112, 114, 113, 115, 117, 116, 118, 120])
    rsi = _calculate_rsi(prices)
    assert 0 <= rsi <= 100


def test_calculate_macd_returns_two_floats():
    prices = pd.Series(np.linspace(100, 200, 100))
    macd, signal = _calculate_macd(prices)
    assert isinstance(macd, float)
    assert isinstance(signal, float)


@patch("agent.data.yf.Ticker")
def test_get_multiple_stocks_skips_failures(mock_ticker):
    good = MagicMock()
    good.info = _make_info()
    good.history.return_value = _make_hist()

    bad = MagicMock()
    bad.info = {}
    bad.history.return_value = pd.DataFrame()

    mock_ticker.side_effect = [good, bad, good]

    results = get_multiple_stocks(["RELIANCE", "BADSTOCK", "TCS"])
    assert len(results) == 2
    assert all(r["ticker"] in ("RELIANCE", "TCS") for r in results)


def test_nse_universe_is_non_empty_list():
    assert isinstance(NSE_UNIVERSE, list)
    assert len(NSE_UNIVERSE) >= 30


import json
import datetime


def test_fetch_universe_returns_cached_when_fresh(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.data._CACHE_DIR", tmp_path)
    cache_file = tmp_path / "universe.json"
    cache_file.write_text(json.dumps({
        "tickers": ["RELIANCE", "TCS", "500032.BO"],
        "fetched_at": datetime.datetime.utcnow().isoformat(),
    }))

    with patch("agent.data.requests.get") as mock_get:
        result = fetch_universe(refresh=False)

    mock_get.assert_not_called()
    assert result == ["RELIANCE", "TCS", "500032.BO"]
