# Stock Market AI Agent

A conversational AI agent that screens NSE stocks using fundamental and technical filters, then ranks candidates with AI-generated reasoning in ₹.

> **Replace `YOUR_USERNAME`** in the badge URL below before publishing.

![CI](https://github.com/YOUR_USERNAME/stock-market-agent/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

- **Natural language screening** — type queries like "find large-cap IT stocks with P/E below 15 and RSI below 40"
- **Fundamental filters** — P/E ratio, Market Cap (₹ Crores), Dividend Yield, Debt-to-Equity
- **Technical filters** — RSI-14 (Wilder), 50-day MA, 200-day MA, MACD bullish crossover
- **AI-ranked results** — composite score (0–100) with plain-English reasoning per stock
- **4 LLM providers** — Claude, OpenAI, Perplexity, or Ollama (local, no API key)
- **Free market data** — yfinance, no paid subscription needed
- **Session cache** — stock data fetched once per session, follow-up queries are instant

---

## Quick Start

### Requirements

- Python 3.12+
- An API key for at least one provider (or Ollama running locally)

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/stock-market-agent.git
cd stock-market-agent
pip install -r requirements.txt
```

### 2. Configure API key

```bash
cp .env.example .env
# Open .env and add your key for the provider you want to use
```

### 3. Run

```bash
# Default provider (Claude, set in config/config.yaml)
python main.py

# Choose a specific provider
python main.py --provider claude
python main.py --provider openai
python main.py --provider perplexity
python main.py --provider ollama
```

---

## Provider Setup

| Provider | Requires | Get Key |
|----------|---------|---------|
| **Claude** (default) | `ANTHROPIC_API_KEY` in `.env` | [console.anthropic.com](https://console.anthropic.com) |
| **OpenAI** | `OPENAI_API_KEY` in `.env` | [platform.openai.com](https://platform.openai.com) |
| **Perplexity** | `PERPLEXITY_API_KEY` in `.env` | [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api) |
| **Ollama** | No API key — runs locally | [ollama.com](https://ollama.com) |

### Ollama (100% local, no cost)

```bash
# 1. Install Ollama: https://ollama.com
# 2. Pull a model
ollama pull llama3

# 3. Run the agent
python main.py --provider ollama
```

To change the local model, edit `config/config.yaml`:
```yaml
ollama_model: llama3   # or: mistral, gemma2, phi3, etc.
```

---

## Example Session

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
1      INFY         87       12.4     36.2     ₹1,842         Zero-debt balance sheet with P/E well
                                                               below sector average. RSI at 36 signals
                                                               an oversold entry opportunity.
2      WIPRO        74       11.1     38.9     ₹498           Undervalued vs IT peers; consistent
                                                               dividend of ₹1/share with improving
                                                               operating margins.
3      TECHM        61       18.3     43.1     ₹1,621         Reasonable valuation with improving
                                                               deal pipeline; MACD crossover imminent.

You: show only large-cap stocks
Parsing query...
Found 2 match(es). Ranking with claude...

You: why is INFY ranked first?
Parsing query...
...

You: quit
Goodbye!
```

---

## Supported Filters

| Filter | Example Queries |
|--------|----------------|
| P/E ratio | `"P/E below 15"`, `"low P/E stocks"` |
| RSI (oversold) | `"RSI below 40"`, `"oversold stocks"` |
| Market Cap | `"large-cap"` (>₹20,000 Cr), `"mid-cap"`, `"small-cap"` |
| Sector | `"IT sector"`, `"banking"`, `"pharma"`, `"energy"` |
| Moving Average | `"above 200 DMA"`, `"above 50 DMA"` |
| MACD | `"MACD bullish crossover"` |
| Dividend Yield | `"dividend yield above 2%"` |
| Debt-to-Equity | `"low debt"`, `"debt-to-equity below 1"` |

Filters combine naturally: `"large-cap pharma stocks with P/E below 25 and RSI below 45"`

---

## Stock Universe

The default universe covers **45 Nifty large/mid-cap stocks**:

`RELIANCE`, `TCS`, `HDFCBANK`, `INFY`, `ICICIBANK`, `HINDUNILVR`, `ITC`, `KOTAKBANK`, `LT`, `AXISBANK`, `BAJFINANCE`, `BHARTIARTL`, `ASIANPAINT`, `MARUTI`, `HCLTECH`, `WIPRO`, `ULTRACEMCO`, `SUNPHARMA`, `TATAMOTORS`, `SBIN`, `DRREDDY`, `CIPLA`, `EICHERMOT`, `HEROMOTOCO`, `JSWSTEEL`, `TATASTEEL`, `TECHM`, `APOLLOHOSP`, `TITAN`, `NESTLEIND`, `NTPC`, `POWERGRID`, `ONGC`, `COALINDIA`, `BPCL`, `ADANIPORTS`, `DIVISLAB`, `BAJAJ-AUTO`, `BRITANNIA`, `PIDILITIND`, `GRASIM`, `INDUSINDBK`, `M&M`, `TATACONSUM`, `SHREECEM`

To use a custom list, pass tickers to `run_chat()` directly in code:

```python
from agent.chat import run_chat
from agent.llm import get_provider

llm = get_provider("claude", {})
run_chat(llm, tickers=["INFY", "TCS", "WIPRO", "HCLTECH"])
```

---

## Architecture

```
User Chat Input
    ↓
chat.py  — NL query → FilterCriteria (via LLM parse_query)
    ↓
data.py  — yfinance NSE data + RSI/MACD/MA (fetched once, cached per session)
    ↓
screener.py — deterministic filter, no LLM, pure Python
    ↓
llm.py   — rank + explain (Claude / OpenAI / Perplexity / Ollama)
    ↓
reporter.py — terminal table with ₹ values
```

`data.py` and `screener.py` have zero LLM dependency.
`llm.py` is the only file aware of provider differences.

---

## Project Structure

```
stock-market-agent/
├── agent/
│   ├── chat.py        # Conversational REPL — orchestrates the pipeline
│   ├── data.py        # yfinance fetcher — RSI, MACD, 50/200 DMA
│   ├── llm.py         # LLM provider abstraction (Claude/OpenAI/Perplexity/Ollama)
│   ├── reporter.py    # Terminal table formatter with ₹ values
│   └── screener.py    # Deterministic filter engine (FilterCriteria dataclass)
├── config/
│   └── config.yaml    # Default provider + model names
├── tests/             # 34 unit tests (all mocked, no network calls)
├── .env.example       # API key template
├── Dockerfile
├── main.py            # CLI entry point
└── requirements.txt
```

---

## Configuration

`config/config.yaml` — set default provider and model overrides:

```yaml
provider: claude              # default provider (overridable with --provider)
claude_model: claude-sonnet-4-6
openai_model: gpt-4o
perplexity_model: sonar-pro
ollama_url: http://localhost:11434
ollama_model: llama3
```

---

## Docker

```bash
docker build -t stock-agent .
docker run -it --env-file .env stock-agent

# With a specific provider
docker run -it --env-file .env stock-agent python main.py --provider openai
```

---

## Development

```bash
# Run tests
pytest -v

# Run linter
flake8 agent/ main.py --max-line-length=120
```

---

## License

MIT
