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
