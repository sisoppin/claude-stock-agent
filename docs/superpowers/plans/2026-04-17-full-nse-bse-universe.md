# Full NSE + BSE Universe Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded 45-stock `NSE_UNIVERSE` with a dynamically fetched list of all actively listed equities on NSE (~2,000) and BSE (~5,000), with daily caching and a `--refresh` flag.

**Architecture:** `fetch_universe()` downloads NSE's public equity CSV and BSE's scrip API, deduplicates by preferring `.NS` for stocks on both exchanges, and caches to `cache/universe.json` (24h TTL). `get_multiple_stocks()` gains a daily stock-data cache (`cache/stocks_YYYY-MM-DD.json`) and a `ThreadPoolExecutor(max_workers=20)` for parallel fetching. A `--refresh` flag in `main.py` forces both caches to be bypassed.

**Tech Stack:** Python stdlib (`concurrent.futures`, `pathlib`, `json`, `datetime`, `io`), `requests`, `pandas`, `yfinance` (all already in project).

---

## File Map

| File | Action | What changes |
|------|--------|--------------|
| `.gitignore` | Modify | Add `cache/` |
| `agent/data.py` | Modify | Add `fetch_universe()`, `_fetch_nse_symbols()`, `_fetch_bse_tickers()`, `_CACHE_DIR`/`_UNIVERSE_CACHE` constants; update `get_stock_data()` for exchange suffixes; refactor `get_multiple_stocks()` with threadpool + daily cache |
| `tests/test_data.py` | Modify | Add tests for `fetch_universe()` (cache hit, stale, dedup, fallback, refresh); add tests for new `get_multiple_stocks()` behavior |
| `main.py` | Modify | Add `--refresh` flag, import `fetch_universe`, pass `refresh` through |
| `agent/chat.py` | Modify | Replace `NSE_UNIVERSE` with `fetch_universe()` |

---

## Task 1: Update `.gitignore`

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add `cache/` to `.gitignore`**

Open `.gitignore` and append:
```
# Stock data cache
cache/
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: ignore cache/ directory"
```

---

## Task 2: TDD `fetch_universe()` — cache hit path

**Files:**
- Modify: `tests/test_data.py`
- Modify: `agent/data.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_data.py` (after existing imports, add `import json, datetime, pathlib`):

```python
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
```

Also update the import line at the top of `tests/test_data.py`:
```python
from agent.data import (
    get_stock_data, _calculate_rsi, _calculate_macd,
    get_multiple_stocks, NSE_UNIVERSE, fetch_universe,
)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
source .agent-01/bin/activate && python -m pytest tests/test_data.py::test_fetch_universe_returns_cached_when_fresh -v
```

Expected: `FAILED` — `ImportError: cannot import name 'fetch_universe'`

- [ ] **Step 3: Add cache constants and skeleton `fetch_universe()` to `agent/data.py`**

Add after the existing imports at the top of `agent/data.py`:
```python
import concurrent.futures
import datetime
import io
import json
import pathlib
import requests

_CACHE_DIR = pathlib.Path(__file__).parent.parent / "cache"
_NSE_CSV_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
_BSE_API_URL = (
    "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
    "?Group=&Scripcode=&industry=&segment=Equity&status=Active"
)
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; stock-agent/1.0)"}
```

Then add the function (before `get_stock_data`):
```python
def fetch_universe(refresh: bool = False) -> list:
    """Return all NSE+BSE equity tickers with daily caching.

    NSE tickers are bare symbols (e.g. 'RELIANCE').
    BSE-only tickers include exchange suffix (e.g. '543217.BO').
    Pass refresh=True to ignore the cache and re-fetch.
    """
    _CACHE_DIR.mkdir(exist_ok=True)
    universe_cache = _CACHE_DIR / "universe.json"  # derived here so test patches to _CACHE_DIR work
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
        # BSE API returns either a list or {"Table": [...]}
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
source .agent-01/bin/activate && python -m pytest tests/test_data.py::test_fetch_universe_returns_cached_when_fresh -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add agent/data.py tests/test_data.py
git commit -m "feat: add fetch_universe() with 24h cache hit path"
```

---

## Task 3: TDD `fetch_universe()` — full fetch, dedup, fallback, refresh

**Files:**
- Modify: `tests/test_data.py`
- Modify: `agent/data.py` (already has the implementation — these tests validate it)

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_data.py`:

```python
def test_fetch_universe_fetches_nse_and_bse_when_cache_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.data._CACHE_DIR", tmp_path)
    monkeypatch.setattr("agent.data._UNIVERSE_CACHE", tmp_path / "universe.json")

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

    # RELIANCE appears in both → only NSE version (bare, no .BO)
    assert "RELIANCE" in result
    assert "RELIANCE.BO" not in result
    # IRFC is BSE-only → .BO suffix
    assert "IRFC.BO" in result
    # TCS is NSE-only → bare
    assert "TCS" in result


def test_fetch_universe_falls_back_when_both_sources_fail(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.data._CACHE_DIR", tmp_path)
    monkeypatch.setattr("agent.data._UNIVERSE_CACHE", tmp_path / "universe.json")

    with patch("agent.data.requests.get", side_effect=Exception("network error")):
        result = fetch_universe(refresh=False)

    assert result == list(NSE_UNIVERSE)


def test_fetch_universe_refresh_ignores_fresh_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.data._CACHE_DIR", tmp_path)
    monkeypatch.setattr("agent.data._UNIVERSE_CACHE", tmp_path / "universe.json")

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
    monkeypatch.setattr("agent.data._UNIVERSE_CACHE", tmp_path / "universe.json")

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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
source .agent-01/bin/activate && python -m pytest tests/test_data.py -k "fetch_universe" -v
```

Expected: the new 4 tests `FAILED` or `ERROR`, the cache-hit test `PASSED`.

- [ ] **Step 3: Run all `fetch_universe` tests**

```bash
source .agent-01/bin/activate && python -m pytest tests/test_data.py -k "fetch_universe" -v
```

Expected: all 5 `fetch_universe` tests `PASSED`.

- [ ] **Step 4: Run full suite to confirm no regressions**

```bash
source .agent-01/bin/activate && python -m pytest tests/ -v
```

Expected: all existing tests `PASSED` + 5 new `fetch_universe` tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add agent/data.py tests/test_data.py
git commit -m "feat: fetch_universe() dedup, fallback, refresh — all paths tested"
```

---

## Task 4: Update `get_stock_data()` to handle exchange suffixes

**Files:**
- Modify: `tests/test_data.py`
- Modify: `agent/data.py`

BSE-only tickers from `fetch_universe()` look like `"IRFC.BO"`. The current `get_stock_data` blindly appends `.NS`, producing `IRFC.BO.NS` — wrong. Fix: use the ticker as-is if it already contains a `.`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_data.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
source .agent-01/bin/activate && python -m pytest tests/test_data.py::test_get_stock_data_uses_suffix_as_is_for_bse -v
```

Expected: `FAILED` — ticker called with `"500032.BO.NS"` instead of `"500032.BO"`.

- [ ] **Step 3: Update `get_stock_data()` in `agent/data.py`**

Change the first two lines of `get_stock_data`:
```python
def get_stock_data(ticker: str) -> Optional[dict]:
    """Fetch fundamental and technical data for a single NSE or BSE stock."""
    symbol = ticker if "." in ticker else f"{ticker}.NS"
```

(The rest of the function is unchanged — `symbol` is used for yfinance, `ticker` is stored in the returned dict.)

- [ ] **Step 4: Run all data tests to verify passing**

```bash
source .agent-01/bin/activate && python -m pytest tests/test_data.py -v
```

Expected: all tests `PASSED`, including the existing `test_get_stock_data_appends_ns_suffix` (bare `"RELIANCE"` still gets `.NS`).

- [ ] **Step 5: Commit**

```bash
git add agent/data.py tests/test_data.py
git commit -m "fix: get_stock_data() respects pre-suffixed BSE tickers (e.g. 500032.BO)"
```

---

## Task 5: TDD `get_multiple_stocks()` — threadpool + daily cache

**Files:**
- Modify: `tests/test_data.py`
- Modify: `agent/data.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_data.py`:

```python
@patch("agent.data.yf.Ticker")
def test_get_multiple_stocks_writes_and_reads_daily_cache(mock_ticker, tmp_path, monkeypatch):
    monkeypatch.setattr("agent.data._CACHE_DIR", tmp_path)

    mock_t = MagicMock()
    mock_t.info = _make_info()
    mock_t.history.return_value = _make_hist()
    mock_ticker.return_value = mock_t

    # First call — no cache, fetches from yfinance
    result1 = get_multiple_stocks(["RELIANCE", "TCS"], refresh=False)
    assert len(result1) == 2
    assert mock_ticker.call_count == 2

    mock_ticker.reset_mock()

    # Second call — cache exists, no yfinance calls
    result2 = get_multiple_stocks(["RELIANCE", "TCS"], refresh=False)
    assert len(result2) == 2
    mock_ticker.assert_not_called()


@patch("agent.data.yf.Ticker")
def test_get_multiple_stocks_refresh_bypasses_cache(mock_ticker, tmp_path, monkeypatch):
    monkeypatch.setattr("agent.data._CACHE_DIR", tmp_path)

    mock_t = MagicMock()
    mock_t.info = _make_info()
    mock_t.history.return_value = _make_hist()
    mock_ticker.return_value = mock_t

    # Seed the cache
    get_multiple_stocks(["RELIANCE"], refresh=False)
    mock_ticker.reset_mock()

    # refresh=True should re-fetch despite cache
    get_multiple_stocks(["RELIANCE"], refresh=True)
    assert mock_ticker.call_count == 1


@patch("agent.data.yf.Ticker")
def test_get_multiple_stocks_skips_failures_parallel(mock_ticker, tmp_path, monkeypatch):
    monkeypatch.setattr("agent.data._CACHE_DIR", tmp_path)

    good = MagicMock()
    good.info = _make_info()
    good.history.return_value = _make_hist()

    bad = MagicMock()
    bad.info = {}
    bad.history.return_value = pd.DataFrame()

    mock_ticker.side_effect = [good, bad, good]

    results = get_multiple_stocks(["RELIANCE", "BADSTOCK", "TCS"], refresh=False)
    assert len(results) == 2
    assert all(r["ticker"] in ("RELIANCE", "TCS") for r in results)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
source .agent-01/bin/activate && python -m pytest tests/test_data.py -k "parallel or cache or refresh_bypasses" -v
```

Expected: `FAILED` — `get_multiple_stocks` doesn't accept `refresh` param yet.

- [ ] **Step 3: Refactor `get_multiple_stocks()` in `agent/data.py`**

Replace the existing `get_multiple_stocks` function:

```python
def get_multiple_stocks(tickers: list, refresh: bool = False) -> list:
    """Fetch data for multiple stocks with daily caching and parallel workers.

    Results are cached to cache/stocks_YYYY-MM-DD.json.
    Pass refresh=True to bypass cache and re-fetch.
    """
    _CACHE_DIR.mkdir(exist_ok=True)
    today = datetime.date.today().isoformat()
    cache_file = _CACHE_DIR / f"stocks_{today}.json"

    if not refresh and cache_file.exists():
        try:
            data = json.loads(cache_file.read_text())
            return list(data.values())
        except Exception:
            pass

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(get_stock_data, tickers))

    stocks = [r for r in results if r is not None]

    try:
        cache_file.write_text(json.dumps({s["ticker"]: s for s in stocks}, default=str))
    except Exception as e:
        print(f"Warning: could not write stock cache: {e}")

    return stocks
```

- [ ] **Step 4: Run all data tests**

```bash
source .agent-01/bin/activate && python -m pytest tests/test_data.py -v
```

Expected: all tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add agent/data.py tests/test_data.py
git commit -m "feat: get_multiple_stocks() parallel fetch (20 threads) + daily cache"
```

---

## Task 6: Update `main.py`

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Update imports and add `--refresh` flag**

Replace the entire `main.py`:

```python
import argparse
import datetime
import pathlib

import yaml
from dotenv import load_dotenv

from agent.data import fetch_universe, get_multiple_stocks
from agent.llm import get_provider
from agent.reporter import format_batch_signal_report
from agent.signals import SignalGenerator
from agent.chat import run_chat

_ROOT = pathlib.Path(__file__).parent


def main():
    load_dotenv()

    with open(_ROOT / "config" / "config.yaml") as f:
        config = yaml.safe_load(f)

    parser = argparse.ArgumentParser(
        description="Stock Market AI Agent — NSE+BSE Screener + Signal Generator"
    )
    parser.add_argument(
        "--provider",
        choices=["claude", "openai", "perplexity", "ollama"],
        default=config.get("provider", "claude"),
        help="LLM provider (default: from config.yaml)",
    )
    parser.add_argument(
        "--mode",
        choices=["chat", "signals"],
        default="chat",
        help="chat: conversational REPL (default), signals: batch scan all stocks",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force re-fetch universe and stock data, ignoring today's cache",
    )
    args = parser.parse_args()

    config["provider"] = args.provider
    llm = get_provider(args.provider, config)

    if args.mode == "signals":
        _run_batch_signals(llm, refresh=args.refresh)
    else:
        run_chat(llm, refresh=args.refresh)


def _run_batch_signals(llm, refresh: bool = False):
    """Fetch all NSE+BSE stocks and generate signals for each."""
    universe = fetch_universe(refresh=refresh)
    print(f"\nBatch Signal Scan — {len(universe)} NSE+BSE stocks")
    print(f"Provider : {llm.provider}")
    print("Fetching data (first run ~5 min, cached runs instant)...\n")

    stocks = get_multiple_stocks(universe, refresh=refresh)
    stock_data = {s["ticker"]: s for s in stocks}

    if not stocks:
        print("No stock data retrieved. Check your internet connection.")
        return

    print(f"Generating signals for {len(stocks)} stocks with {llm.provider}...")
    gen = SignalGenerator(llm)
    signals = gen.generate(stocks)

    date = datetime.date.today().isoformat()
    print(format_batch_signal_report(signals, stock_data, date, llm.provider))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run full test suite**

```bash
source .agent-01/bin/activate && python -m pytest tests/ -v
```

Expected: all tests `PASSED`.

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: main.py uses fetch_universe() and --refresh flag"
```

---

## Task 7: Update `agent/chat.py`

**Files:**
- Modify: `agent/chat.py`

- [ ] **Step 1: Replace `NSE_UNIVERSE` with `fetch_universe()`**

Replace the entire `agent/chat.py`:

```python
import dataclasses
import sys
from agent.data import fetch_universe, get_multiple_stocks
from agent.screener import screen_stocks, FilterCriteria
from agent.llm import LLMProvider
from agent.reporter import format_signal_table, format_signal_detail
from agent.signals import SignalGenerator


def run_chat(llm: LLMProvider, refresh: bool = False):
    """Start the conversational stock screening REPL."""
    universe = fetch_universe(refresh=refresh)
    print("\nStock Market AI Agent (NSE+BSE)")
    print(f"Provider : {llm.provider}")
    print(f"Universe : {len(universe)} stocks")
    print("Type 'quit' to exit\n")

    stock_cache = None
    signal_gen = SignalGenerator(llm)

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
            valid_fields = {f.name for f in dataclasses.fields(FilterCriteria)}
            clean = {k: v for k, v in criteria_dict.items() if v is not None and k in valid_fields}
            criteria = FilterCriteria(**clean)

            if stock_cache is None:
                print(f"Fetching data for {len(universe)} stocks (first run ~5 min, cached runs instant)...")
                stocks = get_multiple_stocks(universe, refresh=False)
                stock_cache = {s["ticker"]: s for s in stocks}
            stocks = list(stock_cache.values())

            matched = screen_stocks(stocks, criteria)

            if not matched:
                print("No stocks matched your criteria. Try relaxing the filters.\n")
                continue

            print(f"Found {len(matched)} match(es). Ranking and generating signals with {llm.provider}...")
            ranked = llm.analyze(matched, query)
            signals = signal_gen.generate(matched)
            print(format_signal_table(ranked, signals, stock_cache))
            print(format_signal_detail(signals))
            print()

        except Exception as e:
            print(f"Error: {e}\n")
```

- [ ] **Step 2: Run full test suite**

```bash
source .agent-01/bin/activate && python -m pytest tests/ -v
```

Expected: all tests `PASSED`.

- [ ] **Step 3: Commit and push**

```bash
git add agent/chat.py
git commit -m "feat: chat.py uses fetch_universe() for full NSE+BSE universe"
git push
```

---

## Task 8: Final verification

- [ ] **Step 1: Run the complete test suite one last time**

```bash
source .agent-01/bin/activate && python -m pytest tests/ -v --tb=short
```

Expected: all tests `PASSED` (51 original + ~9 new = ~60 total).

- [ ] **Step 2: Smoke-test `fetch_universe()` live (optional — requires internet)**

```bash
source .agent-01/bin/activate && python -c "
from agent.data import fetch_universe
tickers = fetch_universe(refresh=True)
nse = [t for t in tickers if '.' not in t]
bse = [t for t in tickers if '.BO' in t]
print(f'Total: {len(tickers)} | NSE: {len(nse)} | BSE-only: {len(bse)}')
print('Sample NSE:', nse[:5])
print('Sample BSE:', bse[:5])
"
```

Expected output similar to:
```
Total: 5234 | NSE: 1847 | BSE-only: 3387
Sample NSE: ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK']
Sample BSE: ['IRFC.BO', '20MICRONS.BO', '21STCENMGM.BO', ...]
```
