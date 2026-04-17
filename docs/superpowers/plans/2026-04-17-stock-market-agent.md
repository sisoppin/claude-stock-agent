# Stock Market AI Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a conversational NSE/BSE stock screener that ranks candidates using fundamental + technical filters and explains results via Claude, OpenAI, Perplexity, or Ollama.

**Architecture:** Multi-layer pipeline: `data.py` fetches yfinance data → `screener.py` applies deterministic filters → `llm.py` ranks + reasons → `reporter.py` formats terminal output. `chat.py` owns the REPL loop, translating natural language into filter criteria via the active LLM. Only `llm.py` knows about providers.

**Tech Stack:** Python 3.12, yfinance, pandas, anthropic SDK, openai SDK, requests (Perplexity + Ollama), pyyaml, python-dotenv, pytest, flake8

---

## File Map

| File | Role |
|------|------|
| `agent/__init__.py` | Empty package marker |
| `agent/data.py` | Fetch NSE stock data from yfinance; calculate RSI, MACD, MAs |
| `agent/screener.py` | `FilterCriteria` dataclass + `screen_stocks()` — pure Python, no LLM |
| `agent/llm.py` | `LLMProvider` class with `analyze()` and `parse_query()` — single abstraction for all 4 providers |
| `agent/reporter.py` | `format_report()` — renders ranked stocks as terminal table in ₹ |
| `agent/chat.py` | `run_chat()` — conversational REPL, orchestrates the full pipeline |
| `main.py` | CLI entry point — loads config, parses `--provider` flag, starts chat |
| `config/config.yaml` | Default provider + Ollama settings |
| `.env.example` | API key template |
| `tests/__init__.py` | Empty package marker |
| `tests/test_data.py` | Unit tests for data layer (mocked yfinance) |
| `tests/test_screener.py` | Unit tests for filter logic with fixture stocks |
| `tests/test_llm.py` | Unit tests for all 4 providers (mocked APIs) + `parse_query` |
| `tests/test_reporter.py` | Unit tests for report formatting |
| `Dockerfile` | Container image for the agent |
| `.github/workflows/ci.yml` | GitHub Actions: install → lint → test |
| `README.md` | Full setup guide, provider config, example output |
| `docs/examples/sample_output.txt` | Sample terminal session for GitHub |

---

## Task 1: Project Scaffold

**Files:**
- Create: `agent/__init__.py`
- Create: `tests/__init__.py`
- Create: `config/config.yaml`
- Create: `.env.example`
- Create: `requirements.txt`
- Create: `pytest.ini`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p agent config tests docs/examples .github/workflows
```

- [ ] **Step 2: Create `agent/__init__.py` and `tests/__init__.py`**

Both files are empty — they just mark the directories as Python packages.

`agent/__init__.py`: (empty file)
`tests/__init__.py`: (empty file)

- [ ] **Step 3: Create `requirements.txt`**

```
yfinance==0.2.51
pandas==2.2.3
anthropic==0.40.0
openai==1.57.0
requests==2.32.3
pyyaml==6.0.2
python-dotenv==1.0.1
pytest==8.3.4
flake8==7.1.1
```

- [ ] **Step 4: Create `config/config.yaml`**

```yaml
provider: claude
ollama_url: http://localhost:11434
ollama_model: llama3
```

- [ ] **Step 5: Create `.env.example`**

```
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
PERPLEXITY_API_KEY=
```

- [ ] **Step 6: Create `pytest.ini`**

```ini
[pytest]
testpaths = tests
```

- [ ] **Step 7: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install without errors.

- [ ] **Step 8: Verify pytest is discoverable**

```bash
pytest --collect-only
```

Expected: `no tests ran` (no test files yet) — no errors.

- [ ] **Step 9: Commit**

```bash
git add agent/__init__.py tests/__init__.py config/config.yaml .env.example requirements.txt pytest.ini
git commit -m "chore: project scaffold — dependencies, config, package structure"
```

---

## Task 2: Data Layer (TDD)

**Files:**
- Create: `tests/test_data.py`
- Create: `agent/data.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_data.py`:

```python
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from agent.data import get_stock_data, _calculate_rsi, _calculate_macd, get_multiple_stocks, NSE_UNIVERSE


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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_data.py -v
```

Expected: `ImportError` — `agent.data` does not exist yet.

- [ ] **Step 3: Implement `agent/data.py`**

```python
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_data.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/data.py tests/test_data.py
git commit -m "feat: data layer — yfinance NSE fetcher with RSI, MACD, moving averages"
```

---

## Task 3: Screener Engine (TDD)

**Files:**
- Create: `tests/test_screener.py`
- Create: `agent/screener.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_screener.py`:

```python
import pytest
from agent.screener import screen_stocks, FilterCriteria

# market_cap in rupees: 1 crore = 1e7 rupees
SAMPLE_STOCKS = [
    {
        "ticker": "INFY", "sector": "Technology", "price": 1842.0,
        "pe_ratio": 12.4, "market_cap": 7_600_000_000_000,  # ~7.6 lakh crore = 76000 cr
        "dividend_yield": 2.5, "debt_to_equity": 0.0,
        "rsi": 36.2, "ma50": 1800.0, "ma200": 1750.0, "macd_bullish": True,
    },
    {
        "ticker": "RELIANCE", "sector": "Energy", "price": 2800.0,
        "pe_ratio": 24.5, "market_cap": 1_890_000_000_000,  # ~1.89 lakh crore = 18900 cr
        "dividend_yield": 0.5, "debt_to_equity": 35.2,
        "rsi": 62.0, "ma50": 2750.0, "ma200": 2600.0, "macd_bullish": False,
    },
    {
        "ticker": "WIPRO", "sector": "Technology", "price": 498.0,
        "pe_ratio": 11.1, "market_cap": 2_700_000_000_000,  # ~2.7 lakh crore = 27000 cr
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_screener.py -v
```

Expected: `ImportError` — `agent.screener` does not exist yet.

- [ ] **Step 3: Implement `agent/screener.py`**

```python
from dataclasses import dataclass
from typing import Optional


@dataclass
class FilterCriteria:
    max_pe: Optional[float] = None
    min_pe: Optional[float] = None
    min_market_cap_cr: Optional[float] = None   # in crores (1 crore = 1e7 rupees)
    max_market_cap_cr: Optional[float] = None
    min_dividend_yield: Optional[float] = None  # percentage (e.g., 1.5 for 1.5%)
    max_debt_to_equity: Optional[float] = None
    max_rsi: Optional[float] = None
    min_rsi: Optional[float] = None
    above_ma50: Optional[bool] = None
    above_ma200: Optional[bool] = None
    macd_bullish: Optional[bool] = None
    sector: Optional[str] = None


def screen_stocks(stocks: list, criteria: FilterCriteria) -> list:
    """Return stocks that satisfy all specified criteria. None fields are skipped."""
    return [s for s in stocks if _matches(s, criteria)]


def _matches(stock: dict, criteria: FilterCriteria) -> bool:
    pe = stock.get("pe_ratio")
    market_cap = stock.get("market_cap")
    market_cap_cr = (market_cap / 1e7) if market_cap else None
    price = stock.get("price")

    checks = [
        criteria.max_pe is None or (pe is not None and pe <= criteria.max_pe),
        criteria.min_pe is None or (pe is not None and pe >= criteria.min_pe),
        criteria.min_market_cap_cr is None or (market_cap_cr is not None and market_cap_cr >= criteria.min_market_cap_cr),
        criteria.max_market_cap_cr is None or (market_cap_cr is not None and market_cap_cr <= criteria.max_market_cap_cr),
        criteria.min_dividend_yield is None or stock.get("dividend_yield", 0) >= criteria.min_dividend_yield,
        criteria.max_debt_to_equity is None or (stock.get("debt_to_equity") is not None and stock["debt_to_equity"] <= criteria.max_debt_to_equity),
        criteria.max_rsi is None or (stock.get("rsi") is not None and stock["rsi"] <= criteria.max_rsi),
        criteria.min_rsi is None or (stock.get("rsi") is not None and stock["rsi"] >= criteria.min_rsi),
        criteria.above_ma50 is None or (price and stock.get("ma50") and (price > stock["ma50"]) == criteria.above_ma50),
        criteria.above_ma200 is None or (price and stock.get("ma200") and (price > stock["ma200"]) == criteria.above_ma200),
        criteria.macd_bullish is None or stock.get("macd_bullish") == criteria.macd_bullish,
        criteria.sector is None or stock.get("sector", "").lower() == criteria.sector.lower(),
    ]
    return all(checks)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_screener.py -v
```

Expected: all 11 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/screener.py tests/test_screener.py
git commit -m "feat: screener engine — FilterCriteria dataclass + deterministic filter logic"
```

---

## Task 4: LLM Provider Abstraction (TDD)

**Files:**
- Create: `tests/test_llm.py`
- Create: `agent/llm.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_llm.py`:

```python
import pytest
import json
from unittest.mock import patch, MagicMock
from agent.llm import LLMProvider, get_provider

SAMPLE_STOCKS = [
    {"ticker": "INFY", "pe_ratio": 12.4, "rsi": 36.2, "price": 1842.0, "sector": "Technology"},
    {"ticker": "WIPRO", "pe_ratio": 11.1, "rsi": 38.9, "price": 498.0, "sector": "Technology"},
]

SAMPLE_RANKED = [
    {"ticker": "INFY", "rank": 1, "score": 87, "reason": "Strong fundamentals with low P/E relative to sector, oversold RSI signals entry opportunity."},
    {"ticker": "WIPRO", "rank": 2, "score": 74, "reason": "Undervalued vs sector peers with consistent dividend history."},
]

SAMPLE_CRITERIA = {"max_pe": 15, "max_rsi": 40, "sector": "Technology"}


@patch("agent.llm.Anthropic")
def test_analyze_claude_returns_ranked_list(mock_anthropic):
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content[0].text = json.dumps(SAMPLE_RANKED)
    mock_anthropic.return_value = mock_client

    llm = LLMProvider("claude", {})
    result = llm.analyze(SAMPLE_STOCKS, "low P/E IT stocks")

    assert len(result) == 2
    assert result[0]["ticker"] == "INFY"
    assert result[0]["rank"] == 1
    assert result[0]["score"] == 87
    assert "reason" in result[0]


@patch("agent.llm.OpenAI")
def test_analyze_openai_returns_ranked_list(mock_openai):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices[0].message.content = json.dumps(SAMPLE_RANKED)
    mock_openai.return_value = mock_client

    llm = LLMProvider("openai", {})
    result = llm.analyze(SAMPLE_STOCKS, "low P/E IT stocks")

    assert len(result) == 2
    assert result[0]["ticker"] == "INFY"


@patch("agent.llm.requests.post")
def test_analyze_perplexity_returns_ranked_list(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps(SAMPLE_RANKED)}}]
    }
    mock_response.raise_for_status = lambda: None
    mock_post.return_value = mock_response

    llm = LLMProvider("perplexity", {})
    result = llm.analyze(SAMPLE_STOCKS, "low P/E IT stocks")

    assert len(result) == 2
    assert result[1]["ticker"] == "WIPRO"


@patch("agent.llm.requests.post")
def test_analyze_ollama_returns_ranked_list(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {"content": json.dumps(SAMPLE_RANKED)}
    }
    mock_response.raise_for_status = lambda: None
    mock_post.return_value = mock_response

    llm = LLMProvider("ollama", {"ollama_url": "http://localhost:11434", "ollama_model": "llama3"})
    result = llm.analyze(SAMPLE_STOCKS, "low P/E IT stocks")

    assert len(result) == 2


@patch("agent.llm.Anthropic")
def test_analyze_handles_markdown_wrapped_json(mock_anthropic):
    wrapped = f"```json\n{json.dumps(SAMPLE_RANKED)}\n```"
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content[0].text = wrapped
    mock_anthropic.return_value = mock_client

    llm = LLMProvider("claude", {})
    result = llm.analyze(SAMPLE_STOCKS, "query")

    assert len(result) == 2


@patch("agent.llm.Anthropic")
def test_parse_query_returns_filter_dict(mock_anthropic):
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content[0].text = json.dumps(SAMPLE_CRITERIA)
    mock_anthropic.return_value = mock_client

    llm = LLMProvider("claude", {})
    result = llm.parse_query("IT stocks with P/E below 15 and RSI below 40")

    assert result["max_pe"] == 15
    assert result["max_rsi"] == 40
    assert result["sector"] == "Technology"


def test_get_provider_returns_llm_provider():
    provider = get_provider("claude", {})
    assert isinstance(provider, LLMProvider)
    assert provider.provider == "claude"


def test_unknown_provider_raises_value_error():
    llm = LLMProvider("unknown_provider", {})
    with pytest.raises(ValueError, match="Unknown provider: unknown_provider"):
        llm.analyze([], "query")
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_llm.py -v
```

Expected: `ImportError` — `agent.llm` does not exist yet.

- [ ] **Step 3: Implement `agent/llm.py`**

```python
import json
import os
import re
import requests
from anthropic import Anthropic
from openai import OpenAI

ANALYZE_SYSTEM_PROMPT = """You are a stock market analyst specializing in Indian equities (NSE/BSE).
You receive a list of stocks that passed screening filters, with their metrics.
Your job:
1. Rank them from best to worst investment candidate (1 = best)
2. Assign a composite score 0-100
3. Write 2-3 sentences of plain-English reasoning per stock (reference ₹ values)

Return ONLY valid JSON — no markdown, no explanation:
[{"ticker": "X", "rank": 1, "score": 87, "reason": "..."}]"""

PARSE_SYSTEM_PROMPT = """You are a JSON parser for stock screening queries.
Return ONLY valid JSON with these optional keys (null for unspecified):
{"max_pe": null, "min_pe": null, "min_market_cap_cr": null, "max_market_cap_cr": null,
 "min_dividend_yield": null, "max_debt_to_equity": null, "max_rsi": null, "min_rsi": null,
 "above_ma50": null, "above_ma200": null, "macd_bullish": null, "sector": null}

Rules:
- "large-cap" → min_market_cap_cr: 20000
- "mid-cap"   → min_market_cap_cr: 5000, max_market_cap_cr: 20000
- "small-cap" → max_market_cap_cr: 5000
- "IT sector" or "technology" → sector: "Technology"
- "P/E below 15" → max_pe: 15
- "RSI below 40" → max_rsi: 40
- "above 200 DMA" → above_ma200: true
- "MACD bullish" → macd_bullish: true"""


class LLMProvider:
    def __init__(self, provider: str, config: dict):
        self.provider = provider
        self.config = config

    def analyze(self, stocks: list, query: str) -> list:
        """Rank and explain screened stocks. Returns list of dicts with rank/score/reason."""
        prompt = f"User query: {query}\n\nStocks:\n{json.dumps(stocks, indent=2, default=str)}"
        text = self._complete(prompt, ANALYZE_SYSTEM_PROMPT)
        return self._extract_json(text)

    def parse_query(self, query: str) -> dict:
        """Translate natural language query into FilterCriteria field dict."""
        prompt = f'Parse this stock screening query: "{query}"'
        text = self._complete(prompt, PARSE_SYSTEM_PROMPT)
        return self._extract_json(text)

    def _complete(self, prompt: str, system: str) -> str:
        if self.provider == "claude":
            return self._call_claude(prompt, system)
        elif self.provider == "openai":
            return self._call_openai(prompt, system)
        elif self.provider == "perplexity":
            return self._call_perplexity(prompt, system)
        elif self.provider == "ollama":
            return self._call_ollama(prompt, system)
        raise ValueError(f"Unknown provider: {self.provider}")

    def _extract_json(self, text: str):
        """Parse JSON from LLM response, stripping markdown code blocks if present."""
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            text = match.group(1)
        return json.loads(text.strip())

    def _call_claude(self, prompt: str, system: str) -> str:
        client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def _call_openai(self, prompt: str, system: str) -> str:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content

    def _call_perplexity(self, prompt: str, system: str) -> str:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {os.environ.get('PERPLEXITY_API_KEY', '')}"},
            json={
                "model": "sonar-pro",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            },
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def _call_ollama(self, prompt: str, system: str) -> str:
        url = self.config.get("ollama_url", "http://localhost:11434")
        model = self.config.get("ollama_model", "llama3")
        response = requests.post(
            f"{url}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            },
        )
        response.raise_for_status()
        return response.json()["message"]["content"]


def get_provider(name: str, config: dict) -> LLMProvider:
    return LLMProvider(provider=name, config=config)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_llm.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/llm.py tests/test_llm.py
git commit -m "feat: LLM provider abstraction — Claude, OpenAI, Perplexity, Ollama via unified interface"
```

---

## Task 5: Reporter (TDD)

**Files:**
- Create: `tests/test_reporter.py`
- Create: `agent/reporter.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_reporter.py`:

```python
import pytest
from agent.reporter import format_report

RANKED = [
    {"ticker": "INFY", "rank": 1, "score": 87, "reason": "Strong fundamentals with low P/E relative to sector."},
    {"ticker": "WIPRO", "rank": 2, "score": 74, "reason": "Undervalued vs sector peers with consistent dividend."},
]

STOCK_DATA = {
    "INFY": {"pe_ratio": 12.4, "rsi": 36.2, "price": 1842.0},
    "WIPRO": {"pe_ratio": 11.1, "rsi": 38.9, "price": 498.0},
}


def test_format_report_contains_all_tickers():
    report = format_report(RANKED, STOCK_DATA)
    assert "INFY" in report
    assert "WIPRO" in report


def test_format_report_contains_rupee_symbol():
    report = format_report(RANKED, STOCK_DATA)
    assert "₹" in report


def test_format_report_ranked_order():
    report = format_report(RANKED, STOCK_DATA)
    assert report.find("INFY") < report.find("WIPRO")


def test_format_report_contains_scores():
    report = format_report(RANKED, STOCK_DATA)
    assert "87" in report
    assert "74" in report


def test_format_report_contains_pe_and_rsi():
    report = format_report(RANKED, STOCK_DATA)
    assert "12.4" in report
    assert "36.2" in report


def test_format_report_empty_list():
    report = format_report([], {})
    assert "No stocks matched" in report


def test_format_report_handles_missing_stock_data():
    # ranked contains a ticker not in stock_data — should not crash
    report = format_report(RANKED, {})
    assert "INFY" in report
    assert "WIPRO" in report
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_reporter.py -v
```

Expected: `ImportError` — `agent.reporter` does not exist yet.

- [ ] **Step 3: Implement `agent/reporter.py`**

```python
def format_report(ranked_stocks: list, stock_data: dict) -> str:
    """Render ranked stocks as a terminal table with ₹ values."""
    if not ranked_stocks:
        return "No stocks matched your criteria. Try relaxing the filters."

    header = f"\n{'RANK':<6} {'TICKER':<12} {'SCORE':<8} {'P/E':<8} {'RSI':<8} {'PRICE (₹)':<14} REASON"
    divider = "-" * 95
    lines = [header, divider]

    for item in sorted(ranked_stocks, key=lambda x: x["rank"]):
        ticker = item.get("ticker", "")
        data = stock_data.get(ticker, {})

        pe = data.get("pe_ratio")
        rsi = data.get("rsi")
        price = data.get("price", 0)

        pe_str = f"{pe:.1f}" if isinstance(pe, (int, float)) else "N/A"
        rsi_str = f"{rsi:.1f}" if isinstance(rsi, (int, float)) else "N/A"
        price_str = f"₹{price:,.0f}" if price else "N/A"
        reason = item.get("reason", "")[:60]

        lines.append(
            f"{item['rank']:<6} {ticker:<12} {item['score']:<8} {pe_str:<8} {rsi_str:<8} {price_str:<14} {reason}"
        )

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_reporter.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
pytest -v
```

Expected: all tests across all test files PASS.

- [ ] **Step 6: Commit**

```bash
git add agent/reporter.py tests/test_reporter.py
git commit -m "feat: reporter — terminal table formatter with ₹ values and ranked output"
```

---

## Task 6: Chat Interface

**Files:**
- Create: `agent/chat.py`

No unit tests for this file — it's a REPL that owns I/O. Integration is verified manually in Task 7.

- [ ] **Step 1: Implement `agent/chat.py`**

```python
import sys
from agent.data import get_multiple_stocks, NSE_UNIVERSE
from agent.screener import screen_stocks, FilterCriteria
from agent.llm import LLMProvider
from agent.reporter import format_report


def run_chat(llm: LLMProvider, tickers: list = None):
    """Start the conversational stock screening REPL."""
    universe = tickers or NSE_UNIVERSE
    print(f"\nStock Market AI Agent (NSE)")
    print(f"Provider : {llm.provider}")
    print(f"Universe : {len(universe)} stocks")
    print("Type 'quit' to exit\n")

    stock_cache = {}

    while True:
        try:
            query = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            sys.exit(0)

        if not query:
            continue
        if query.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        try:
            print("Parsing query...")
            criteria_dict = llm.parse_query(query)
            # Remove None values so FilterCriteria uses its own defaults
            clean = {k: v for k, v in criteria_dict.items() if v is not None}
            criteria = FilterCriteria(**clean)

            if not stock_cache:
                print(f"Fetching data for {len(universe)} stocks (this may take ~30s)...")
                stocks = get_multiple_stocks(universe)
                stock_cache = {s["ticker"]: s for s in stocks}
            else:
                stocks = list(stock_cache.values())

            matched = screen_stocks(stocks, criteria)

            if not matched:
                print("No stocks matched your criteria. Try relaxing the filters.\n")
                continue

            print(f"Found {len(matched)} match(es). Ranking with {llm.provider}...")
            ranked = llm.analyze(matched, query)
            print(format_report(ranked, stock_cache))
            print()

        except Exception as e:
            print(f"Error: {e}\n")
```

- [ ] **Step 2: Verify import works**

```bash
python -c "from agent.chat import run_chat; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add agent/chat.py
git commit -m "feat: chat interface — conversational REPL with session stock cache"
```

---

## Task 7: Main Entry Point

**Files:**
- Create: `main.py`

- [ ] **Step 1: Implement `main.py`**

```python
import argparse
import os

import yaml
from dotenv import load_dotenv

from agent.llm import get_provider
from agent.chat import run_chat


def main():
    load_dotenv()

    with open("config/config.yaml") as f:
        config = yaml.safe_load(f)

    parser = argparse.ArgumentParser(
        description="Stock Market AI Agent — NSE/BSE Screener"
    )
    parser.add_argument(
        "--provider",
        choices=["claude", "openai", "perplexity", "ollama"],
        default=config.get("provider", "claude"),
        help="LLM provider (default: from config.yaml)",
    )
    args = parser.parse_args()

    config["provider"] = args.provider
    llm = get_provider(args.provider, config)
    run_chat(llm)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify CLI help works**

```bash
python main.py --help
```

Expected output:
```
usage: main.py [-h] [--provider {claude,openai,perplexity,ollama}]
Stock Market AI Agent — NSE/BSE Screener
...
```

- [ ] **Step 3: Run full test suite one more time**

```bash
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 4: Run flake8 lint**

```bash
flake8 agent/ main.py --max-line-length=120
```

Expected: no output (zero lint errors).

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat: main entry point — CLI with --provider flag and config.yaml default"
```

---

## Task 8: DevOps — Docker, CI, README, Examples

**Files:**
- Create: `Dockerfile`
- Create: `.github/workflows/ci.yml`
- Create: `docs/examples/sample_output.txt`
- Create: `README.md`

- [ ] **Step 1: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

- [ ] **Step 2: Create `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Lint
        run: flake8 agent/ main.py --max-line-length=120

      - name: Test
        run: pytest tests/ -v
```

- [ ] **Step 3: Create `docs/examples/sample_output.txt`**

```
$ python main.py --provider claude

Stock Market AI Agent (NSE)
Provider : claude
Universe : 45 stocks
Type 'quit' to exit

You: find IT sector stocks with P/E below 20 and RSI below 45
Parsing query...
Fetching data for 45 stocks (this may take ~30s)...
Found 3 match(es). Ranking with claude...

RANK   TICKER       SCORE    P/E      RSI      PRICE (₹)      REASON
-----------------------------------------------------------------------------------------------
1      INFY         87       12.4     36.2     ₹1,842         Strong balance sheet with zero debt
                                                               and P/E well below sector average.
                                                               Oversold RSI at 36 signals a
                                                               potential entry point.
2      WIPRO        74       11.1     38.9     ₹498           Undervalued vs sector peers with
                                                               consistent dividend history of ₹1/share.
3      TECHM        61       18.3     43.1     ₹1,621         Reasonable valuation with improving
                                                               order book; MACD crossover expected.

You: quit
Goodbye!
```

- [ ] **Step 4: Create `README.md`**

```markdown
# Stock Market AI Agent 🇮🇳

A conversational AI agent that screens NSE/BSE stocks using fundamental and technical filters, then ranks candidates with AI-generated reasoning.

![CI](https://github.com/YOUR_USERNAME/stock-market-agent/actions/workflows/ci.yml/badge.svg)

## Features

- **Natural language screening** — "find large-cap IT stocks with P/E below 15 and RSI below 40"
- **Fundamental filters** — P/E, Market Cap, EPS, Dividend Yield, Debt-to-Equity
- **Technical filters** — RSI, 50/200 DMA, MACD
- **AI-ranked results** — composite score + plain-English reasoning in ₹
- **4 LLM providers** — Claude, OpenAI, Perplexity, Ollama (local)
- **Free market data** — yfinance (no API key needed for data)

## Setup

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/stock-market-agent.git
cd stock-market-agent
pip install -r requirements.txt
```

### 2. Configure API keys

```bash
cp .env.example .env
# Edit .env and add your key for the provider you want to use
```

```
ANTHROPIC_API_KEY=your_key_here    # for --provider claude
OPENAI_API_KEY=your_key_here       # for --provider openai
PERPLEXITY_API_KEY=your_key_here   # for --provider perplexity
# Ollama needs no API key — just have it running locally
```

### 3. Set default provider (optional)

Edit `config/config.yaml`:

```yaml
provider: claude   # change to: openai | perplexity | ollama
```

## Usage

```bash
# Use default provider from config.yaml
python main.py

# Override provider at runtime
python main.py --provider openai
python main.py --provider ollama
python main.py --provider perplexity
```

## Example Session

```
You: find large-cap NSE stocks with P/E below 15 and RSI below 40
Agent: Scanning 45 stocks... found 4 matches. Ranking with Claude...

RANK   TICKER   SCORE   P/E    RSI    PRICE (₹)   REASON
1      INFY     87      12.4   36.2   ₹1,842      Strong fundamentals...
2      WIPRO    74      11.1   38.9   ₹498        Undervalued vs peers...

You: show only banking sector
You: explain why INFY is ranked #1
```

## Ollama (Local Model)

1. Install Ollama: https://ollama.com
2. Pull a model: `ollama pull llama3`
3. Run: `python main.py --provider ollama`

Edit `config/config.yaml` to change the model:
```yaml
ollama_model: llama3   # or: mistral, gemma2, etc.
```

## Docker

```bash
docker build -t stock-agent .
docker run -it --env-file .env stock-agent
```

## Running Tests

```bash
pytest -v
```

## Supported Filters

| Filter | Example Query |
|--------|--------------|
| P/E ratio | "P/E below 15" |
| RSI | "RSI below 40 (oversold)" |
| Market Cap | "large-cap", "mid-cap", "small-cap" |
| Sector | "IT sector", "banking", "pharma" |
| Moving Average | "above 200 DMA", "above 50 DMA" |
| MACD | "MACD bullish" |
| Dividend Yield | "dividend yield above 2%" |
| Debt-to-Equity | "low debt" |

## License

MIT
```

- [ ] **Step 5: Commit all DevOps files**

```bash
git add Dockerfile .github/workflows/ci.yml docs/examples/sample_output.txt README.md
git commit -m "chore: Docker, GitHub Actions CI, README with setup guide and example output"
```

- [ ] **Step 6: Final full test + lint run**

```bash
pytest -v && flake8 agent/ main.py --max-line-length=120
```

Expected: all tests pass, zero lint errors.

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|-----------------|------|
| NSE/BSE via yfinance | Task 2 (`data.py`) |
| Fundamental filters (P/E, Market Cap, EPS, Yield, D/E) | Task 3 (`screener.py`) |
| Technical filters (RSI, 50/200 DMA, MACD) | Task 2 + Task 3 |
| Ranked output with score + reasoning | Task 4 (`llm.py` → `analyze`) |
| Natural language → filter criteria | Task 4 (`llm.py` → `parse_query`) |
| Claude / OpenAI / Perplexity / Ollama | Task 4 (`llm.py`) |
| Config default + runtime --provider flag | Task 7 (`main.py`) |
| ₹ formatting in output | Task 5 (`reporter.py`) |
| Conversational REPL with session cache | Task 6 (`chat.py`) |
| requirements.txt, .env.example | Task 1 |
| Dockerfile | Task 8 |
| GitHub Actions CI | Task 8 |
| README with setup + examples | Task 8 |

All requirements covered. No gaps.

**Type consistency check:**

- `get_stock_data(ticker: str) -> Optional[dict]` — used in `get_multiple_stocks` ✓
- `get_multiple_stocks(tickers: list) -> list` — used in `chat.py` ✓
- `screen_stocks(stocks: list, criteria: FilterCriteria) -> list` — used in `chat.py` ✓
- `FilterCriteria(**clean)` — `clean` keys match `FilterCriteria` fields exactly ✓
- `llm.analyze(matched, query) -> list[dict]` — passed to `format_report` ✓
- `llm.parse_query(query) -> dict` — unpacked as `FilterCriteria(**clean)` ✓
- `format_report(ranked_stocks: list, stock_data: dict) -> str` — called in `chat.py` ✓
- `get_provider(name: str, config: dict) -> LLMProvider` — used in `main.py` ✓
