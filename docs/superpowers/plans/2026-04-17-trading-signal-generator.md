# Trading Signal Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add BUY/SELL/HOLD trading signals (with confidence score, ₹ entry zone, stop-loss, and AI reasoning) to every screened result in chat, plus a `--mode signals` batch scan across all 45 NSE stocks.

**Architecture:** New `agent/signals.py` holds `SignalGenerator` which calls the existing `LLMProvider._complete()` with a signal-specific prompt. `reporter.py` gets three new formatting functions. `chat.py` calls `SignalGenerator.generate()` after `llm.analyze()` and passes results to the updated reporter. `main.py` gains a `--mode` flag. `data.py`, `screener.py`, and `llm.py` are untouched.

**Tech Stack:** Python 3.12, existing `anthropic`/`openai`/`requests` SDKs (via `LLMProvider`), `pytest` + `unittest.mock`

---

## File Map

| File | Change |
|------|--------|
| `agent/signals.py` | **Create** — `SignalGenerator` class + `SIGNAL_SYSTEM_PROMPT` |
| `agent/reporter.py` | **Modify** — add `format_signal_table()`, `format_signal_detail()`, `format_batch_signal_report()` |
| `agent/chat.py` | **Modify** — import `SignalGenerator`, call after `analyze()`, use new reporter functions |
| `main.py` | **Modify** — add `--mode {chat,signals}` argument, implement batch scan flow |
| `tests/test_signals.py` | **Create** — unit tests for `SignalGenerator` |
| `tests/test_reporter.py` | **Modify** — add tests for three new reporter functions |

---

## Task 1: SignalGenerator (TDD)

**Files:**
- Create: `tests/test_signals.py`
- Create: `agent/signals.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_signals.py`:

```python
import json
from unittest.mock import MagicMock
from agent.signals import SignalGenerator

SAMPLE_STOCKS = [
    {
        "ticker": "INFY", "pe_ratio": 12.4, "rsi": 36.2, "price": 1842.0,
        "macd_bullish": True, "ma50": 1800.0, "ma200": 1750.0,
        "dividend_yield": 2.5, "debt_to_equity": 0.0, "sector": "Technology",
    },
    {
        "ticker": "RELIANCE", "pe_ratio": 24.5, "rsi": 62.0, "price": 2800.0,
        "macd_bullish": False, "ma50": 2750.0, "ma200": 2600.0,
        "dividend_yield": 0.5, "debt_to_equity": 35.2, "sector": "Energy",
    },
]

SAMPLE_SIGNALS = [
    {
        "ticker": "INFY", "signal": "BUY", "confidence": 82,
        "entry_zone": "₹1,800–₹1,850", "stop_loss": "₹1,680",
        "reasoning": "RSI oversold at 36 with price above 200 DMA and zero debt.",
    },
    {
        "ticker": "RELIANCE", "signal": "HOLD", "confidence": 55,
        "entry_zone": "₹2,750–₹2,810", "stop_loss": "₹2,580",
        "reasoning": "Neutral momentum; awaiting MACD confirmation above signal line.",
    },
]


def _mock_llm(response):
    llm = MagicMock()
    llm._complete.return_value = json.dumps(response)
    llm._extract_json.return_value = response
    return llm


def test_generate_returns_signal_list():
    gen = SignalGenerator(_mock_llm(SAMPLE_SIGNALS))
    result = gen.generate(SAMPLE_STOCKS)
    assert len(result) == 2
    assert result[0]["ticker"] == "INFY"
    assert result[0]["signal"] == "BUY"
    assert result[0]["confidence"] == 82
    assert "entry_zone" in result[0]
    assert "stop_loss" in result[0]
    assert "reasoning" in result[0]


def test_generate_empty_stocks_returns_empty_without_calling_llm():
    llm = _mock_llm([])
    gen = SignalGenerator(llm)
    result = gen.generate([])
    assert result == []
    llm._complete.assert_not_called()


def test_generate_calls_llm_with_ticker_in_prompt():
    llm = _mock_llm(SAMPLE_SIGNALS)
    gen = SignalGenerator(llm)
    gen.generate(SAMPLE_STOCKS)
    llm._complete.assert_called_once()
    prompt = llm._complete.call_args[0][0]
    assert "INFY" in prompt
    assert "RELIANCE" in prompt


def test_generate_signal_values_are_valid():
    gen = SignalGenerator(_mock_llm(SAMPLE_SIGNALS))
    result = gen.generate(SAMPLE_STOCKS)
    for sig in result:
        assert sig["signal"] in ("BUY", "SELL", "HOLD")
        assert 0 <= sig["confidence"] <= 100


def test_generate_uses_signal_system_prompt():
    from agent.signals import SIGNAL_SYSTEM_PROMPT
    assert "BUY" in SIGNAL_SYSTEM_PROMPT
    assert "SELL" in SIGNAL_SYSTEM_PROMPT
    assert "HOLD" in SIGNAL_SYSTEM_PROMPT
    assert "stop" in SIGNAL_SYSTEM_PROMPT.lower()
    assert "entry" in SIGNAL_SYSTEM_PROMPT.lower()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_signals.py -v
```

Expected: `ImportError` — `agent.signals` does not exist yet.

- [ ] **Step 3: Implement `agent/signals.py`**

```python
import json
from agent.llm import LLMProvider

SIGNAL_SYSTEM_PROMPT = """You are a professional stock market analyst specializing in Indian equities (NSE).
You receive stock data including both technical indicators and fundamental metrics.
For each stock, generate a trading signal based on ALL available data.

Technical signals to consider:
- RSI < 40: oversold (bullish), RSI > 70: overbought (bearish)
- Price above 200 DMA: long-term uptrend, below: downtrend
- Price above 50 DMA: short-term momentum positive
- MACD bullish (True): momentum turning positive

Fundamental signals to consider:
- Low P/E vs sector: undervalued (bullish)
- High debt-to-equity (>1): financial risk (bearish)
- Dividend yield > 1%: income support (neutral to bullish)

For each stock output:
1. signal: BUY (setup is favourable), SELL (deteriorating), or HOLD (neutral/unclear)
2. confidence: 0-100 reflecting signal strength
3. entry_zone: suggested ₹ price range to enter (near current support level)
4. stop_loss: ₹ price where the thesis is invalidated
5. reasoning: 2-3 sentences combining technical + fundamental factors, reference ₹ values

Return ONLY valid JSON — no markdown, no explanation:
[{"ticker": "X", "signal": "BUY", "confidence": 82, "entry_zone": "₹1,800–₹1,850", "stop_loss": "₹1,680", "reasoning": "..."}]"""


class SignalGenerator:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def generate(self, stocks: list) -> list:
        """Generate BUY/SELL/HOLD signals for a list of stocks using LLM analysis."""
        if not stocks:
            return []
        prompt = (
            f"Generate trading signals for these {len(stocks)} NSE stocks:\n"
            f"{json.dumps(stocks, indent=2, default=str)}"
        )
        text = self.llm._complete(prompt, SIGNAL_SYSTEM_PROMPT)
        return self.llm._extract_json(text)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_signals.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Run full suite to confirm no regressions**

```bash
pytest -v
```

Expected: all 34 existing + 5 new = 39 tests PASS.

- [ ] **Step 6: Flake8**

```bash
flake8 agent/signals.py --max-line-length=120
```

Expected: no output.

- [ ] **Step 7: Commit**

```bash
git add agent/signals.py tests/test_signals.py
git commit -m "feat: SignalGenerator — BUY/SELL/HOLD signals via LLM with entry zone and stop-loss"
```

---

## Task 2: Reporter Signal Functions (TDD)

**Files:**
- Modify: `tests/test_reporter.py`
- Modify: `agent/reporter.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_reporter.py`:

```python
# --- Signal reporter tests ---

RANKED = [
    {"ticker": "INFY", "rank": 1, "score": 87, "reason": "Strong fundamentals."},
    {"ticker": "WIPRO", "rank": 2, "score": 74, "reason": "Undervalued vs peers."},
]
SIGNALS = [
    {
        "ticker": "INFY", "signal": "BUY", "confidence": 82,
        "entry_zone": "₹1,800–₹1,850", "stop_loss": "₹1,680",
        "reasoning": "RSI oversold, above 200 DMA, zero debt.",
    },
    {
        "ticker": "WIPRO", "signal": "HOLD", "confidence": 61,
        "entry_zone": "₹490–₹505", "stop_loss": "₹460",
        "reasoning": "Neutral momentum, awaiting MACD confirmation.",
    },
]
STOCK_DATA_SIG = {
    "INFY": {"pe_ratio": 12.4, "rsi": 36.2, "price": 1842.0},
    "WIPRO": {"pe_ratio": 11.1, "rsi": 38.9, "price": 498.0},
}


# format_signal_table tests
def test_signal_table_contains_signal_column():
    from agent.reporter import format_signal_table
    report = format_signal_table(RANKED, SIGNALS, STOCK_DATA_SIG)
    assert "BUY" in report
    assert "HOLD" in report


def test_signal_table_contains_confidence():
    from agent.reporter import format_signal_table
    report = format_signal_table(RANKED, SIGNALS, STOCK_DATA_SIG)
    assert "82" in report
    assert "61" in report


def test_signal_table_contains_tickers():
    from agent.reporter import format_signal_table
    report = format_signal_table(RANKED, SIGNALS, STOCK_DATA_SIG)
    assert "INFY" in report
    assert "WIPRO" in report


def test_signal_table_contains_rupee_symbol():
    from agent.reporter import format_signal_table
    report = format_signal_table(RANKED, SIGNALS, STOCK_DATA_SIG)
    assert "₹" in report


def test_signal_table_empty_returns_no_match_message():
    from agent.reporter import format_signal_table
    report = format_signal_table([], [], {})
    assert "No stocks matched" in report


# format_signal_detail tests
def test_signal_detail_contains_entry_zone():
    from agent.reporter import format_signal_detail
    detail = format_signal_detail(SIGNALS)
    assert "₹1,800" in detail
    assert "₹490" in detail


def test_signal_detail_contains_stop_loss():
    from agent.reporter import format_signal_detail
    detail = format_signal_detail(SIGNALS)
    assert "₹1,680" in detail
    assert "₹460" in detail


def test_signal_detail_contains_ticker_and_signal():
    from agent.reporter import format_signal_detail
    detail = format_signal_detail(SIGNALS)
    assert "INFY" in detail
    assert "BUY" in detail
    assert "WIPRO" in detail
    assert "HOLD" in detail


def test_signal_detail_empty_returns_empty_string():
    from agent.reporter import format_signal_detail
    assert format_signal_detail([]) == ""


# format_batch_signal_report tests
def test_batch_report_contains_all_tickers():
    from agent.reporter import format_batch_signal_report
    report = format_batch_signal_report(SIGNALS, STOCK_DATA_SIG, "2026-04-17", "claude")
    assert "INFY" in report
    assert "WIPRO" in report


def test_batch_report_contains_date_and_provider():
    from agent.reporter import format_batch_signal_report
    report = format_batch_signal_report(SIGNALS, STOCK_DATA_SIG, "2026-04-17", "claude")
    assert "2026-04-17" in report
    assert "claude" in report


def test_batch_report_contains_entry_and_stop():
    from agent.reporter import format_batch_signal_report
    report = format_batch_signal_report(SIGNALS, STOCK_DATA_SIG, "2026-04-17", "claude")
    assert "₹1,800" in report
    assert "₹1,680" in report
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_reporter.py -v
```

Expected: 12 new tests FAIL with `ImportError` (functions not yet defined).

- [ ] **Step 3: Add three functions to `agent/reporter.py`**

Append to the end of `agent/reporter.py` (keep the existing `format_report` function untouched):

```python
def format_signal_table(ranked: list, signals: list, stock_data: dict) -> str:
    """Merged table: rank/score/signal/confidence/P-E/RSI/price/reason."""
    if not ranked:
        return "No stocks matched your criteria. Try relaxing the filters."

    sig_map = {s["ticker"]: s for s in signals}
    header = (
        f"\n{'RANK':<6} {'TICKER':<12} {'SCORE':<8} {'SIGNAL':<8} {'CONF':<6}"
        f"{'P/E':<8} {'RSI':<8} {'PRICE (₹)':<14} REASON"
    )
    divider = "-" * 110
    lines = [header, divider]

    for item in sorted(ranked, key=lambda x: x["rank"]):
        ticker = item.get("ticker", "")
        data = stock_data.get(ticker, {})
        sig = sig_map.get(ticker, {})

        pe = data.get("pe_ratio")
        rsi = data.get("rsi")
        price = data.get("price", 0)

        pe_str = f"{pe:.1f}" if isinstance(pe, (int, float)) and not math.isnan(pe) else "N/A"
        rsi_str = f"{rsi:.1f}" if isinstance(rsi, (int, float)) and not math.isnan(rsi) else "N/A"
        price_str = f"₹{price:,.0f}" if price is not None else "N/A"
        signal_str = sig.get("signal", "N/A")
        conf_str = str(sig.get("confidence", "N/A"))
        reason = item.get("reason", "")[:80]

        lines.append(
            f"{item['rank']:<6} {ticker:<12} {item['score']:<8} {signal_str:<8} {conf_str:<6}"
            f"{pe_str:<8} {rsi_str:<8} {price_str:<14} {reason}"
        )

    return "\n".join(lines)


def format_signal_detail(signals: list) -> str:
    """Detailed per-stock breakdown: entry zone, stop-loss, full analysis."""
    if not signals:
        return ""
    lines = []
    for sig in signals:
        ticker = sig.get("ticker", "")
        signal = sig.get("signal", "N/A")
        conf = sig.get("confidence", "N/A")
        bar = "─" * max(1, 52 - len(ticker))
        lines.append(f"\n── {ticker} — {signal} (Confidence: {conf}/100) {bar}")
        lines.append(f"  Entry Zone : {sig.get('entry_zone', 'N/A')}")
        lines.append(f"  Stop Loss  : {sig.get('stop_loss', 'N/A')}")
        lines.append(f"  Analysis   : {sig.get('reasoning', 'N/A')}")
    return "\n".join(lines)


def format_batch_signal_report(
    signals: list, stock_data: dict, date: str, provider: str
) -> str:
    """Full signal report for --mode signals batch scan."""
    header = f"\nSTOCK SIGNAL REPORT — {date}  (Provider: {provider})"
    divider = "=" * 60
    col_header = (
        f"{'TICKER':<12} {'SIGNAL':<8} {'CONF':<6} {'PRICE (₹)':<14}"
        f"{'ENTRY ZONE':<24} STOP LOSS"
    )
    col_divider = "-" * 90
    lines = [header, divider, col_header, col_divider]

    for sig in signals:
        ticker = sig.get("ticker", "")
        data = stock_data.get(ticker, {})
        price = data.get("price", 0)
        price_str = f"₹{price:,.0f}" if price is not None else "N/A"
        entry = sig.get("entry_zone", "N/A")
        stop = sig.get("stop_loss", "N/A")
        lines.append(
            f"{ticker:<12} {sig.get('signal', 'N/A'):<8} {sig.get('confidence', 'N/A'):<6}"
            f"{price_str:<14} {entry:<24} {stop}"
        )

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_reporter.py -v
```

Expected: all 7 existing + 12 new = 19 reporter tests PASS.

- [ ] **Step 5: Run full suite**

```bash
pytest -v
```

Expected: all 39 + 12 = 51 tests PASS.

- [ ] **Step 6: Flake8**

```bash
flake8 agent/reporter.py --max-line-length=120
```

Expected: no output.

- [ ] **Step 7: Commit**

```bash
git add agent/reporter.py tests/test_reporter.py
git commit -m "feat: reporter — signal table, detail breakdown, batch report formatting"
```

---

## Task 3: Integrate Signals into Chat

**Files:**
- Modify: `agent/chat.py`

No new unit tests — the chat REPL is integration behaviour. Verified by import check.

- [ ] **Step 1: Read current `agent/chat.py`**

Verify the current imports and the line that calls `format_report`:
```
from agent.reporter import format_report          # line 6
print(format_report(ranked, stock_cache))         # line 54
```

- [ ] **Step 2: Update `agent/chat.py`**

Replace the entire file with:

```python
import dataclasses
import sys
from agent.data import get_multiple_stocks, NSE_UNIVERSE
from agent.screener import screen_stocks, FilterCriteria
from agent.llm import LLMProvider
from agent.reporter import format_signal_table, format_signal_detail
from agent.signals import SignalGenerator


def run_chat(llm: LLMProvider, tickers: list = None):
    """Start the conversational stock screening REPL."""
    universe = tickers or NSE_UNIVERSE
    print("\nStock Market AI Agent (NSE)")
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
                print(f"Fetching data for {len(universe)} stocks (this may take ~30s)...")
                fetched = get_multiple_stocks(universe)
                stock_cache = {s["ticker"]: s for s in fetched}
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

- [ ] **Step 3: Verify import works**

```bash
python -c "from agent.chat import run_chat; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Run full test suite**

```bash
pytest -v
```

Expected: all 51 tests PASS (chat has no unit tests, so count stays at 51).

- [ ] **Step 5: Flake8**

```bash
flake8 agent/chat.py --max-line-length=120
```

Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add agent/chat.py
git commit -m "feat: chat — integrate SignalGenerator, show merged signal table + detail after every screen"
```

---

## Task 4: Batch Scan Mode + README Update

**Files:**
- Modify: `main.py`
- Modify: `README.md`

- [ ] **Step 1: Read current `main.py`**

Current file ends at line 36. The `run_chat(llm)` call is on line 32.

- [ ] **Step 2: Replace `main.py`**

```python
import argparse
import datetime
import pathlib

import yaml
from dotenv import load_dotenv

from agent.data import get_multiple_stocks, NSE_UNIVERSE
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
        description="Stock Market AI Agent — NSE Screener + Signal Generator"
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
    args = parser.parse_args()

    config["provider"] = args.provider
    llm = get_provider(args.provider, config)

    if args.mode == "signals":
        _run_batch_signals(llm)
    else:
        run_chat(llm)


def _run_batch_signals(llm):
    """Fetch all NSE stocks and generate signals for each."""
    print(f"\nBatch Signal Scan — {len(NSE_UNIVERSE)} NSE stocks")
    print(f"Provider : {llm.provider}")
    print("Fetching data (this may take ~60s)...\n")

    stocks = get_multiple_stocks(NSE_UNIVERSE)
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

- [ ] **Step 3: Verify CLI help shows both flags**

```bash
python main.py --help
```

Expected output includes:
```
--mode {chat,signals}
```

- [ ] **Step 4: Run full test suite**

```bash
pytest -v
```

Expected: all 51 tests PASS.

- [ ] **Step 5: Flake8 full project**

```bash
flake8 agent/ main.py --max-line-length=120
```

Expected: no output.

- [ ] **Step 6: Update README.md — add signals section**

In `README.md`, find the `## Example Session` section and add a new `## Trading Signals` section directly before it:

```markdown
## Trading Signals

Every screening result automatically includes a **BUY / SELL / HOLD signal** with confidence score, AI-suggested entry price zone (₹), and stop-loss level.

### In Chat (automatic with every screen)

```
You: find oversold IT stocks with P/E below 20
...

RANK  TICKER   SCORE  SIGNAL  CONF  P/E    RSI    PRICE (₹)   REASON
1     INFY     87     BUY     82    12.4   36.2   ₹1,842      Strong fundamentals...
2     WIPRO    74     HOLD    61    11.1   38.9   ₹498        Undervalued but...

── INFY — BUY (Confidence: 82/100) ────────────────────────────────
  Entry Zone : ₹1,800–₹1,850
  Stop Loss  : ₹1,680
  Analysis   : RSI recovering from oversold (36.2), price above 200 DMA,
               P/E at 12.4 below sector average. Zero debt strengthens case.

── WIPRO — HOLD (Confidence: 61/100) ──────────────────────────────
  Entry Zone : ₹490–₹505
  Stop Loss  : ₹460
  Analysis   : Neutral momentum with MACD yet to confirm bullish crossover.
               Wait for RSI to establish direction before entering.
```

### Batch Scan (all 45 stocks, no filter)

```bash
python main.py --mode signals
# or with a specific provider
python main.py --mode signals --provider ollama
```

Output:
```
STOCK SIGNAL REPORT — 2026-04-17  (Provider: claude)
============================================================
TICKER       SIGNAL  CONF   PRICE (₹)      ENTRY ZONE               STOP LOSS
RELIANCE     BUY     79     ₹2,800         ₹2,750–₹2,810            ₹2,580
TCS          HOLD    65     ₹3,421         ₹3,380–₹3,430            ₹3,200
HDFCBANK     BUY     88     ₹1,720         ₹1,700–₹1,730            ₹1,580
...
```

> **Disclaimer:** Signals are AI-generated for research purposes only. Not financial advice. Always do your own due diligence before making any investment decisions.
```

- [ ] **Step 7: Commit everything**

```bash
git add main.py README.md
git commit -m "feat: --mode signals batch scan + README trading signals section"
```

---

## Self-Review

**Spec coverage:**

| Spec Requirement | Task |
|---|---|
| BUY/SELL/HOLD signal per stock | Task 1 (`signals.py`) |
| Confidence score 0–100 | Task 1 (`signals.py`) |
| AI-suggested entry zone (₹) | Task 1 (`SIGNAL_SYSTEM_PROMPT`) |
| AI-suggested stop-loss (₹) | Task 1 (`SIGNAL_SYSTEM_PROMPT`) |
| Technical + Fundamental data in signal | Task 1 (`SIGNAL_SYSTEM_PROMPT`) |
| Signals auto-appended to every chat result | Task 3 (`chat.py`) |
| Summary table with SIGNAL + CONFIDENCE columns | Task 2 (`format_signal_table`) |
| Detailed breakdown per stock | Task 2 (`format_signal_detail`) |
| Batch scan `--mode signals` | Task 4 (`main.py`) |
| Batch scan full report format | Task 2 (`format_batch_signal_report`) |
| `data.py`, `screener.py`, `llm.py` untouched | All tasks — verified |

All requirements covered. No gaps.

**Type consistency:**

- `SignalGenerator(llm: LLMProvider)` — used in `chat.py` and `main.py` ✓
- `SignalGenerator.generate(stocks: list) -> list` — called with `matched` (list of stock dicts) ✓
- `format_signal_table(ranked: list, signals: list, stock_data: dict) -> str` — called in `chat.py` with `ranked`, `signals`, `stock_cache` ✓
- `format_signal_detail(signals: list) -> str` — called in `chat.py` with `signals` ✓
- `format_batch_signal_report(signals: list, stock_data: dict, date: str, provider: str) -> str` — called in `main.py` `_run_batch_signals` ✓
- `llm._complete(prompt, system)` and `llm._extract_json(text)` — both are public-underscore methods on `LLMProvider`, used in `signals.py` ✓
