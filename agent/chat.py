import dataclasses
import sys
from agent.data import fetch_universe, get_multiple_stocks
from agent.screener import screen_stocks, FilterCriteria
from agent.llm import LLMProvider
from agent.reporter import format_signal_table, format_signal_detail
from agent.signals import SignalGenerator
from agent.progress import StepTracker


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

        tracker = StepTracker()
        try:
            tracker.step(f"Parsing query with {llm.provider}")
            criteria_dict = llm.parse_query(query)
            valid_fields = {f.name for f in dataclasses.fields(FilterCriteria)}
            clean = {k: v for k, v in criteria_dict.items() if v is not None and k in valid_fields}
            criteria = FilterCriteria(**clean)

            if stock_cache is None:
                tracker.step(f"Fetching data for {len(universe)} stocks (cached after first run)")
                stocks = get_multiple_stocks(universe, refresh=False)
                stock_cache = {s["ticker"]: s for s in stocks}
            else:
                tracker.step("Using cached stock data")

            stocks = list(stock_cache.values())

            tracker.step(f"Screening {len(stocks)} stocks against filters")
            matched = screen_stocks(stocks, criteria)

            if not matched:
                tracker.done()
                print("No stocks matched your criteria. Try relaxing the filters.\n")
                continue

            tracker.step(f"AI ranking {len(matched)} match(es) with {llm.provider}")
            ranked = llm.analyze(matched, query)

            tracker.step(f"Generating signals for {len(matched)} stock(s)")
            signals = signal_gen.generate(matched)

            tracker.done()
            print(format_signal_table(ranked, signals, stock_cache))
            print(format_signal_detail(signals))
            print()

        except Exception as e:
            tracker.done()
            print(f"Error: {e}\n")
