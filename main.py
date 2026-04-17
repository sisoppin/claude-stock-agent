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
