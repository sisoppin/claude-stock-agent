# Trading Signal Generator — Design Spec
**Date:** 2026-04-17
**Status:** Approved

---

## Overview

Add a Trading Signal Generator to the existing Stock Market AI Agent. For every screened stock result, the agent automatically generates a BUY / SELL / HOLD signal with confidence score, AI-suggested entry price zone (₹), stop-loss (₹), and plain-English reasoning. A batch scan mode (`--mode signals`) scans all 45 stocks and outputs a full signal report without filtering.

---

## Goals

- Automatically append BUY/SELL/HOLD signal to every chat screening result
- Provide confidence score (0–100), AI-suggested entry zone (₹), and stop-loss (₹) per stock
- Signals based on both technical (RSI, MACD, 50/200 DMA) and fundamental (P/E, debt, dividend) data
- Entry price zone and stop-loss determined by LLM (not hardcoded rules)
- Batch scan mode: `python main.py --mode signals` scans all 45 stocks, no filtering
- All prices in ₹ (Indian Rupees)

---

## Architecture

New file `agent/signals.py` added to the existing pipeline. Existing files `data.py`, `screener.py`, `llm.py` remain untouched. `reporter.py`, `chat.py`, and `main.py` are extended.

```
User Chat Input
    ↓
chat.py — NL query → FilterCriteria (via LLM parse_query)
    ↓
data.py — yfinance NSE data (unchanged)
    ↓
screener.py — deterministic filter (unchanged)
    ↓
llm.py → analyze()               → ranked list (existing)
signals.py → SignalGenerator      → calls llm.py internally → signal list (NEW)
    ↓
reporter.py — merged table + detailed breakdown (extended)
```

---

## New File: `agent/signals.py`

### `SignalGenerator` class

```python
class SignalGenerator:
    def __init__(self, llm: LLMProvider): ...
    def generate(self, stocks: list) -> list: ...
```

- `generate(stocks)` sends all stock data (technical + fundamental) to the LLM with a signal-specific system prompt
- Returns a list of signal dicts, one per stock:

```python
{
    "ticker": "INFY",
    "signal": "BUY",            # BUY | SELL | HOLD
    "confidence": 82,            # 0–100
    "entry_zone": "₹1,800–₹1,850",
    "stop_loss": "₹1,680",
    "reasoning": "RSI recovering from oversold (36.2), price above 200 DMA..."
}
```

### Signal System Prompt

Instructs the LLM to:
1. Assess each stock using both technical signals (RSI, MACD, DMA) and fundamentals (P/E, D/E, dividend yield)
2. Output BUY if setup is favourable, SELL if deteriorating, HOLD if neutral/unclear
3. Suggest entry zone as a ₹ range near current price support
4. Suggest stop-loss as a ₹ level where the thesis is invalidated
5. Return ONLY valid JSON — no markdown

---

## Modified Files

### `agent/reporter.py`

Add two new functions:

**`format_signal_table(ranked, signals, stock_data) -> str`**
Merged terminal table with existing columns (RANK, TICKER, SCORE, P/E, RSI, PRICE ₹) plus new columns (SIGNAL, CONFIDENCE).

**`format_signal_detail(signals) -> str`**
Detailed per-stock breakdown block showing entry zone, stop-loss, and full reasoning.

**`format_batch_signal_report(signals, stock_data, date, provider) -> str`**
Full report for `--mode signals` batch scan: header with date/provider, then one row per stock (TICKER, SIGNAL, CONFIDENCE, PRICE ₹, ENTRY ZONE, STOP LOSS).

### `agent/chat.py`

After `llm.analyze()` returns ranked results, call `SignalGenerator.generate()` on the same matched stocks. Pass both to the updated reporter functions. No change to the fetch/screen/parse flow.

### `main.py`

Add `--mode` argument with choices `["chat", "signals"]` (default: `"chat"`).

- `--mode chat` → existing behaviour (unchanged)
- `--mode signals` → fetch all 45 stocks, skip screener, run `SignalGenerator.generate()` on all, print `format_batch_signal_report()`

---

## Output Format

### Chat Mode — Merged Table

```
RANK  TICKER       SCORE  SIGNAL  CONF  P/E    RSI    PRICE (₹)   REASON
-------------------------------------------------------------------------------------
1     INFY         87     BUY     82    12.4   36.2   ₹1,842      Strong fundamentals...
2     WIPRO        74     HOLD    61    11.1   38.9   ₹498        Undervalued but...
3     TECHM        55     SELL    70    18.3   43.1   ₹1,621      Weakening momentum...
```

### Chat Mode — Detailed Breakdown (follows table)

```
── INFY — BUY (Confidence: 82/100) ──────────────────────────
  Entry Zone : ₹1,800 – ₹1,850
  Stop Loss  : ₹1,680
  Analysis   : RSI recovering from oversold (36.2), price above 200 DMA,
               P/E at 12.4 is below 5-year avg. Strong order book with
               consistent dividend. Risk is global IT slowdown.
```

### Batch Mode (`--mode signals`)

```
STOCK SIGNAL REPORT — 2026-04-17  (Provider: claude)
=====================================================
TICKER       SIGNAL  CONF   PRICE (₹)    ENTRY ZONE           STOP LOSS
RELIANCE     BUY     79     ₹2,800       ₹2,750 – ₹2,810      ₹2,580
TCS          HOLD    65     ₹3,421       ₹3,380 – ₹3,430      ₹3,200
HDFCBANK     BUY     88     ₹1,720       ₹1,700 – ₹1,730      ₹1,580
```

---

## Testing Strategy

- `tests/test_signals.py` — mock `LLMProvider`, verify `SignalGenerator.generate()` returns correct dict structure, handles unknown keys, handles missing stocks
- `tests/test_reporter.py` — extend with tests for `format_signal_table`, `format_signal_detail`, `format_batch_signal_report` — verify ₹ formatting, BUY/SELL/HOLD present, correct column order

---

## Out of Scope

- Actual trade execution
- Price alerts or notifications
- Historical signal backtesting
- Charting or visualisation
- Stop-loss calculated via hardcoded rules (LLM decides)
- BSE stocks (NSE only, matching existing scope)
