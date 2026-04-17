# Stock Market AI Agent

A conversational AI agent that screens NSE/BSE stocks using fundamental and technical filters, then ranks candidates with AI-generated reasoning.

![CI](https://github.com/YOUR_USERNAME/stock-market-agent/actions/workflows/ci.yml/badge.svg)

## Features

- **Natural language screening** — "find large-cap IT stocks with P/E below 15 and RSI below 40"
- **Fundamental filters** — P/E, Market Cap (₹), EPS, Dividend Yield, Debt-to-Equity
- **Technical filters** — RSI (14-day Wilder), 50/200 DMA, MACD
- **AI-ranked results** — composite score + plain-English reasoning in ₹
- **4 LLM providers** — Claude, OpenAI, Perplexity, Ollama (local, no API key)
- **Free market data** — yfinance (no API key needed for data)

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/stock-market-agent.git
cd stock-market-agent
pip install -r requirements.txt
```

### 2. Configure API keys

```bash
cp .env.example .env
# Edit .env — add your key for the provider you want to use
```

### 3. Run

```bash
python main.py --provider claude
```

## Provider Setup

| Provider | Command | Requires |
|----------|---------|---------|
| Claude (default) | `python main.py` | `ANTHROPIC_API_KEY` in `.env` |
| OpenAI | `python main.py --provider openai` | `OPENAI_API_KEY` in `.env` |
| Perplexity | `python main.py --provider perplexity` | `PERPLEXITY_API_KEY` in `.env` |
| Ollama (local) | `python main.py --provider ollama` | [Ollama](https://ollama.com) running locally |

### Ollama Setup (no API key)

```bash
# Install Ollama from https://ollama.com
ollama pull llama3
python main.py --provider ollama
```

Change model in `config/config.yaml`:
```yaml
ollama_model: llama3   # or: mistral, gemma2, etc.
```

## Example Session

```
You: find large-cap NSE stocks with P/E below 15 and RSI below 40
Parsing query...
Fetching data for 45 stocks (this may take ~30s)...
Found 4 match(es). Ranking with claude...

RANK   TICKER   SCORE   P/E    RSI    PRICE (₹)   REASON
1      INFY     87      12.4   36.2   ₹1,842      Strong fundamentals with low P/E...
2      WIPRO    74      11.1   38.9   ₹498        Undervalued vs sector peers...

You: show only banking sector
You: explain why INFY is ranked 1
```

## Supported Filters

| Filter | Example Query |
|--------|--------------|
| P/E ratio | "P/E below 15", "low P/E stocks" |
| RSI (oversold) | "RSI below 40", "oversold stocks" |
| Market Cap | "large-cap" (>₹20,000Cr), "mid-cap", "small-cap" |
| Sector | "IT sector", "banking", "pharma", "energy" |
| Moving Average | "above 200 DMA", "above 50 DMA" |
| MACD | "MACD bullish crossover" |
| Dividend Yield | "dividend yield above 2%" |
| Debt-to-Equity | "low debt", "debt-to-equity below 1" |

## Docker

```bash
docker build -t stock-agent .
docker run -it --env-file .env stock-agent
```

## Running Tests

```bash
pytest -v
```

## Architecture

```
User Chat Input
    ↓
chat.py  — NL query → FilterCriteria (via LLM)
    ↓
screener.py — deterministic filter (no LLM)
    ↓
data.py  — yfinance NSE data + RSI/MACD/MA
    ↓
llm.py   — rank + explain (Claude/OpenAI/Perplexity/Ollama)
    ↓
reporter.py — terminal table with ₹ values
```

## Configuration

`config/config.yaml` — set default provider and model names:

```yaml
provider: claude
claude_model: claude-sonnet-4-6
openai_model: gpt-4o
perplexity_model: sonar-pro
ollama_url: http://localhost:11434
ollama_model: llama3
```

## License

MIT
