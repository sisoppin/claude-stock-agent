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


@patch("agent.data.yf.Ticker")
def test_get_stock_data_uses_suffix_as_is_for_bse(mock_ticker):
    mock_t = MagicMock()
    mock_t.info = _make_info()
    mock_t.history.return_value = _make_hist()
    mock_ticker.return_value = mock_t

    result = get_stock_data("500032.BO")

    mock_ticker.assert_called_once_with("500032.BO")
    assert result is not None
    assert result["ticker"] == "500032.BO"


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


def test_fetch_universe_fetches_nse_and_bse_when_cache_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.data._CACHE_DIR", tmp_path)

    nse_csv = "SYMBOL,NAME OF COMPANY\nRELIANCE,Reliance Industries\nTCS,Tata Consultancy\n"
    bse_json = [
        {"scrip_id": "RELIANCE", "Scripcode": "500325"},
        {"scrip_id": "IRFC", "Scripcode": "543257"},
    ]

    def fake_get(url, **kwargs):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = lambda: None
        if "nseindia" in url:
            mock_resp.text = nse_csv
        else:
            mock_resp.json.return_value = bse_json
        return mock_resp

    with patch("agent.data.requests.get", side_effect=fake_get):
        result = fetch_universe(refresh=False)

    assert "RELIANCE" in result
    assert "RELIANCE.BO" not in result
    assert "IRFC.BO" in result
    assert "TCS" in result


def test_fetch_universe_falls_back_when_both_sources_fail(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.data._CACHE_DIR", tmp_path)

    with patch("agent.data.requests.get", side_effect=Exception("network error")):
        result = fetch_universe(refresh=False)

    assert result == list(NSE_UNIVERSE)


def test_fetch_universe_refresh_ignores_fresh_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.data._CACHE_DIR", tmp_path)

    cache_file = tmp_path / "universe.json"
    cache_file.write_text(json.dumps({
        "tickers": ["STALE_TICKER"],
        "fetched_at": datetime.datetime.utcnow().isoformat(),
    }))

    nse_csv = "SYMBOL,NAME OF COMPANY\nRELIANCE,Reliance Industries\n"

    def fake_get(url, **kwargs):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = lambda: None
        if "nseindia" in url:
            mock_resp.text = nse_csv
        else:
            mock_resp.json.return_value = []
        return mock_resp

    with patch("agent.data.requests.get", side_effect=fake_get):
        result = fetch_universe(refresh=True)

    assert "RELIANCE" in result
    assert "STALE_TICKER" not in result


def test_fetch_universe_stale_cache_triggers_refetch(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.data._CACHE_DIR", tmp_path)

    old_time = (datetime.datetime.utcnow() - datetime.timedelta(hours=25)).isoformat()
    cache_file = tmp_path / "universe.json"
    cache_file.write_text(json.dumps({
        "tickers": ["OLD_TICKER"],
        "fetched_at": old_time,
    }))

    nse_csv = "SYMBOL,NAME OF COMPANY\nINFY,Infosys\n"

    def fake_get(url, **kwargs):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = lambda: None
        if "nseindia" in url:
            mock_resp.text = nse_csv
        else:
            mock_resp.json.return_value = []
        return mock_resp

    with patch("agent.data.requests.get", side_effect=fake_get):
        result = fetch_universe(refresh=False)

    assert "INFY" in result
    assert "OLD_TICKER" not in result
