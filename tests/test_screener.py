from agent.screener import screen_stocks, FilterCriteria

# market_cap in rupees: 1 crore = 1e7 rupees
SAMPLE_STOCKS = [
    {
        "ticker": "INFY", "sector": "Technology", "price": 1842.0,
        "pe_ratio": 12.4, "market_cap": 7_600_000_000_000,  # ~76000 cr
        "dividend_yield": 2.5, "debt_to_equity": 0.0,
        "rsi": 36.2, "ma50": 1800.0, "ma200": 1750.0, "macd_bullish": True,
    },
    {
        "ticker": "RELIANCE", "sector": "Energy", "price": 2800.0,
        "pe_ratio": 24.5, "market_cap": 1_890_000_000_000,  # ~18900 cr
        "dividend_yield": 0.5, "debt_to_equity": 35.2,
        "rsi": 62.0, "ma50": 2750.0, "ma200": 2600.0, "macd_bullish": False,
    },
    {
        "ticker": "WIPRO", "sector": "Technology", "price": 498.0,
        "pe_ratio": 11.1, "market_cap": 2_700_000_000_000,  # ~27000 cr
        "dividend_yield": 1.0, "debt_to_equity": 0.5,
        "rsi": 38.9, "ma50": 510.0, "ma200": 490.0, "macd_bullish": True,
    },
]


def test_screen_by_max_pe():
    result = screen_stocks(SAMPLE_STOCKS, FilterCriteria(max_pe=15))
    tickers = [s["ticker"] for s in result]
    assert "INFY" in tickers
    assert "WIPRO" in tickers
    assert "RELIANCE" not in tickers


def test_screen_by_max_rsi():
    result = screen_stocks(SAMPLE_STOCKS, FilterCriteria(max_rsi=40))
    tickers = [s["ticker"] for s in result]
    assert "INFY" in tickers
    assert "WIPRO" in tickers
    assert "RELIANCE" not in tickers


def test_screen_by_sector():
    result = screen_stocks(SAMPLE_STOCKS, FilterCriteria(sector="Technology"))
    tickers = [s["ticker"] for s in result]
    assert "INFY" in tickers
    assert "WIPRO" in tickers
    assert "RELIANCE" not in tickers


def test_screen_combined_criteria():
    result = screen_stocks(SAMPLE_STOCKS, FilterCriteria(max_pe=15, max_rsi=40, sector="Technology"))
    tickers = [s["ticker"] for s in result]
    assert "INFY" in tickers
    assert "WIPRO" in tickers
    assert "RELIANCE" not in tickers


def test_screen_no_matches_returns_empty():
    result = screen_stocks(SAMPLE_STOCKS, FilterCriteria(max_pe=5))
    assert result == []


def test_screen_empty_criteria_returns_all():
    result = screen_stocks(SAMPLE_STOCKS, FilterCriteria())
    assert len(result) == 3


def test_screen_above_ma50():
    # INFY: 1842 > 1800 ✓  RELIANCE: 2800 > 2750 ✓  WIPRO: 498 < 510 ✗
    result = screen_stocks(SAMPLE_STOCKS, FilterCriteria(above_ma50=True))
    tickers = [s["ticker"] for s in result]
    assert "INFY" in tickers
    assert "RELIANCE" in tickers
    assert "WIPRO" not in tickers


def test_screen_below_ma50():
    # WIPRO: price 498 < ma50 510 → passes below-MA50 filter
    result = screen_stocks(SAMPLE_STOCKS, FilterCriteria(above_ma50=False))
    tickers = [s["ticker"] for s in result]
    assert "WIPRO" in tickers
    assert "INFY" not in tickers
    assert "RELIANCE" not in tickers


def test_screen_above_ma200():
    # INFY: 1842 > 1750 ✓  RELIANCE: 2800 > 2600 ✓  WIPRO: 498 > 490 ✓
    result = screen_stocks(SAMPLE_STOCKS, FilterCriteria(above_ma200=True))
    assert len(result) == 3


def test_screen_macd_bullish():
    result = screen_stocks(SAMPLE_STOCKS, FilterCriteria(macd_bullish=True))
    tickers = [s["ticker"] for s in result]
    assert "INFY" in tickers
    assert "WIPRO" in tickers
    assert "RELIANCE" not in tickers


def test_screen_min_dividend_yield():
    result = screen_stocks(SAMPLE_STOCKS, FilterCriteria(min_dividend_yield=2.0))
    tickers = [s["ticker"] for s in result]
    assert "INFY" in tickers
    assert "RELIANCE" not in tickers
    assert "WIPRO" not in tickers


def test_screen_min_market_cap_cr():
    # INFY: 7.6e12 / 1e7 = 760000 cr  RELIANCE: 1.89e12/1e7=189000 cr  WIPRO: 2.7e12/1e7=270000 cr
    result = screen_stocks(SAMPLE_STOCKS, FilterCriteria(min_market_cap_cr=500_000))
    tickers = [s["ticker"] for s in result]
    assert "INFY" in tickers
    assert "RELIANCE" not in tickers
    assert "WIPRO" not in tickers
