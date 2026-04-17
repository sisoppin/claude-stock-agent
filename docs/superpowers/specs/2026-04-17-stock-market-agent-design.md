# Stock Market AI Agent — Design Spec
**Date:** 2026-04-17
**Status:** Approved

---

## Overview

A conversational AI agent for screening and recommending Indian stock market (NSE/BSE) candidates. Users interact via natural language chat. The agent fetches live stock data, applies fundamental and technical filters, then uses an LLM to rank and explain results. Supports four LLM providers: Claude, OpenAI, Perplexity, and Ollama (local).

---

## Goals

- Screen NSE/BSE stocks using fundamental + technical criteria
- Rank matched stocks with AI-generated reasoning in ₹
- Support Claude, OpenAI, Perplexity, and Ollama interchangeably
- Provider set via config file, overridable at runtime via CLI flag
- Publishable on GitHub with full setup docs, Docker, and CI

---

## Architecture

Multi-layer pipeline with clean separation between data, screening, and LLM analysis:

```
User Chat Input
    ↓
chat.py — parses natural language → structured filter dict
    ↓
screener.py — applies filters, returns matching stocks + metrics
    ↓
data.py — fetches NSE/BSE data via yfinance (.NS / .BO suffix)
    ↓
llm.py — ranks stocks, generates reasoning (provider-swappable)
    ↓
reporter.py — formats ranked output with ₹ values to terminal
```

`screener.py` and `data.py` have zero LLM dependency and work standalone.
`llm.py` is the only file aware of provider differences.

---

## Project Structure

```
stock-market-agent/
├── agent/
│   ├── __init__.py
│   ├── chat.py            # Chat interface — parses user queries
│   ├── screener.py        # Screening engine — fundamental + technical filters
│   ├── data.py            # Data layer — yfinance fetcher for NSE/BSE
│   ├── llm.py             # LLM provider abstraction
│   └── reporter.py        # Formats ranked output with ₹ values
├── config/
│   └── config.yaml        # Default provider + screening defaults
├── docs/
│   └── examples/          # Sample outputs for GitHub
├── tests/
│   ├── test_screener.py
│   ├── test_data.py
│   └── test_llm.py
├── .env.example
├── .github/
│   └── workflows/ci.yml
├── Dockerfile
├── requirements.txt
├── README.md
└── main.py
```

---

## Data Layer (`data.py`)

- **Source:** `yfinance` (free, no API key, covers NSE/BSE)
- **NSE suffix:** `.NS` (e.g., `RELIANCE.NS`)
- **BSE suffix:** `.BO` (e.g., `RELIANCE.BO`)
- **Default universe:** ~200 NSE large/mid-cap stocks (curated list)
- **Custom tickers:** User can pass their own list

**Data fetched per stock:**

| Category | Fields |
|----------|--------|
| Price | Current price (₹), 52-week high/low, volume |
| Fundamentals | P/E ratio, Market Cap (₹), EPS, Dividend Yield, Debt-to-Equity |
| Technicals | RSI (14-day), 50 DMA, 200 DMA, MACD (calculated from OHLCV history) |

---

## Screening Engine (`screener.py`)

Pure Python — deterministic, no LLM. Accepts a filter dict and returns matching stocks with their raw metrics.

**Supported filters:**

| Type | Examples |
|------|---------|
| Fundamental | P/E < 20, Market Cap > ₹10,000 Cr, Dividend Yield > 1%, Debt-to-Equity < 1 |
| Technical | RSI < 40, Price > 50 DMA, Price > 200 DMA, MACD bullish crossover |
| Combined | Any combination of the above |

`chat.py` uses the active LLM to translate natural language queries into a structured filter dict before passing to screener.

---

## LLM Provider Abstraction (`llm.py`)

Single `LLMProvider` class with a unified `analyze(stocks, query)` method. Routes to the selected provider transparently.

**Supported providers:**

| Provider | Model | API Key Required |
|----------|-------|-----------------|
| `claude` | claude-sonnet-4-6 | `ANTHROPIC_API_KEY` |
| `openai` | gpt-4o | `OPENAI_API_KEY` |
| `perplexity` | sonar-pro | `PERPLEXITY_API_KEY` |
| `ollama` | llama3 / mistral | None (local) |

**Provider selection:**
1. Default in `config/config.yaml` → `provider: claude`
2. Runtime override → `python main.py --provider ollama`

**LLM task:** Receives screened stocks + raw metrics. Outputs ranked list (1–N) with composite score (0–100) and 2–3 sentence reasoning per stock. Returns structured JSON consumed by `reporter.py`.

**Prompt:** Provider-agnostic system prompt works across all four. Ollama uses a trimmed version for smaller context windows.

---

## Chat Interface (`chat.py`)

Conversational loop. Maintains session history for follow-up queries.

**Example session:**
```
You: find large-cap NSE stocks with P/E below 15 and RSI below 40
Agent: Scanning 200 stocks... found 8 matches. Ranking with Claude...

You: show only IT sector
Agent: Filtering to IT sector... 3 matches found.

You: explain why INFY is ranked #1
Agent: [detailed reasoning]
```

---

## Reporter (`reporter.py`)

Formats LLM JSON output into a clean terminal table with ₹ values.

```
RANK  STOCK       SCORE   P/E    RSI    PRICE (₹)    REASON
 1    INFY         87    12.4   36.2   ₹1,842       Strong fundamentals, oversold...
 2    WIPRO         74    11.1   38.9   ₹498         Undervalued vs sector peers...
```

---

## GitHub / DevOps

| Asset | Details |
|-------|---------|
| `requirements.txt` | Pinned: `yfinance`, `pandas`, `ta`, `anthropic`, `openai`, `requests`, `pyyaml`, `python-dotenv` |
| `.env.example` | Template with `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `PERPLEXITY_API_KEY` (blank) |
| `Dockerfile` | Runs chat agent in container |
| `GitHub Actions CI` | On push: install → lint (flake8) → test (pytest) |
| `README.md` | Setup guide, provider config, example outputs in ₹, CI badge |
| `docs/examples/` | Sample terminal output for each provider |

---

## Testing Strategy

- `test_data.py` — mock yfinance responses, verify correct field extraction
- `test_screener.py` — verify filter logic with known fixture stocks
- `test_llm.py` — mock LLM responses, verify JSON parsing and ranking output

---

## Out of Scope

- Actual trade execution (no buy/sell orders placed)
- Portfolio tracking or P&L calculation
- Paid data sources
- Web UI (terminal only)
- US/global markets
