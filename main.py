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
    from agent.progress import StepTracker
    tracker = StepTracker()

    print(f"\nBatch Signal Scan")
    print(f"Provider : {llm.provider}")

    tracker.step("Fetching stock universe (NSE+BSE)")
    universe = fetch_universe(refresh=refresh)

    tracker.step(f"Fetching data for {len(universe)} stocks (cached after first run)")
    stocks = get_multiple_stocks(universe, refresh=refresh)
    stock_data = {s["ticker"]: s for s in stocks}

    if not stocks:
        tracker.done()
        print("No stock data retrieved. Check your internet connection.")
        return

    tracker.step(f"Generating signals for {len(stocks)} stocks with {llm.provider}")
    gen = SignalGenerator(llm)
    signals = gen.generate(stocks)
    tracker.done()

    date = datetime.date.today().isoformat()
    print(format_batch_signal_report(signals, stock_data, date, llm.provider))


if __name__ == "__main__":
    main()
