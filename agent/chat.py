import dataclasses
import re
import sys
from agent.data import fetch_universe, get_multiple_stocks
from agent.screener import screen_stocks, FilterCriteria
from agent.llm import LLMProvider
from agent.reporter import format_signal_table, format_signal_detail
from agent.signals import SignalGenerator
from agent.progress import StepTracker
from agent import user

HELP_TEXT = """
📖 Commands:
  watch TICKER          — add stock to watchlist
  unwatch TICKER        — remove from watchlist
  watchlist             — show your watchlist
  watchlist signals     — get signals for watchlist stocks

  buy QTY TICKER at PRICE  — add holding (e.g. buy 100 GRSE at 1800)
  sell TICKER              — remove holding
  portfolio                — show portfolio with live P&L

  prefer sectors IT,Pharma — set preferred sectors
  prefer max_pe 20         — set max P/E preference
  prefer clear             — clear all preferences
  preferences              — show current preferences

  help                  — show this help
  quit                  — exit

  Anything else         — natural language stock query
"""


def run_chat(llm: LLMProvider, refresh: bool = False):
    """Start the conversational stock screening REPL."""
    universe = fetch_universe(refresh=refresh)
    print("\n🤖 Stock Market AI Assistant (NSE+BSE)")
    print(f"Provider : {llm.provider}")
    print(f"Universe : {len(universe)} stocks")

    wl = user.get_watchlist()
    pf = user.get_portfolio()
    if wl:
        print(f"Watchlist: {', '.join(wl[:10])}{'...' if len(wl) > 10 else ''}")
    if pf:
        print(f"Portfolio: {len(pf)} holding(s)")
    print("Type 'help' for commands, or just ask a question\n")

    stock_cache = None
    signal_gen = SignalGenerator(llm)
    history = []

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
        if query.lower() == "help":
            print(HELP_TEXT)
            continue

        # ── Command routing ────────────────────────────────
        handled = _handle_command(query, llm, signal_gen, stock_cache, universe, refresh)
        if handled is not None:
            if handled == "__CACHE_NEEDED__":
                stock_cache = _ensure_cache(stock_cache, universe)
                handled = _handle_command(query, llm, signal_gen, stock_cache, universe, refresh)
            if handled is not None:
                print(handled)
                print()
                continue

        # ── Stock screening query ──────────────────────────
        history.append({"role": "user", "content": query})
        tracker = StepTracker()
        try:
            tracker.step(f"Parsing query with {llm.provider}")
            criteria_dict = llm.parse_query(query, history=history)
            valid_fields = {f.name for f in dataclasses.fields(FilterCriteria)}
            clean = {k: v for k, v in criteria_dict.items() if v is not None and k in valid_fields}

            # Apply user preferences as defaults
            prefs = user.get_preferences()
            if prefs.get("sectors") and "sector" not in clean:
                if len(prefs["sectors"]) == 1:
                    clean["sector"] = prefs["sectors"][0]
            for pkey in ("max_pe", "max_debt_to_equity", "min_dividend_yield"):
                if prefs.get(pkey) is not None and pkey not in clean:
                    clean[pkey] = prefs[pkey]

            criteria = FilterCriteria(**clean)

            stock_cache = _ensure_cache(stock_cache, universe, tracker)
            stocks = list(stock_cache.values())

            tracker.step(f"Screening {len(stocks)} stocks against filters")
            matched = screen_stocks(stocks, criteria)

            # Fallback: if no match and query looks like a ticker name, try ticker search
            if not matched and not criteria.ticker_search:
                words = [w.upper() for w in query.split() if w.isalpha() and len(w) >= 2]
                for word in words:
                    fallback = screen_stocks(stocks, FilterCriteria(ticker_search=word))
                    if fallback:
                        matched = fallback
                        break

            if not matched:
                tracker.done()
                resp = "No stocks matched your criteria. Try relaxing the filters."
                print(resp)
                history.append({"role": "assistant", "content": resp})
                print()
                continue

            # Cap results sent to LLM to avoid timeouts
            MAX_LLM_STOCKS = 20
            if len(matched) > MAX_LLM_STOCKS:
                print(f"  ℹ️  {len(matched)} matches found, analyzing top {MAX_LLM_STOCKS}")
                matched = matched[:MAX_LLM_STOCKS]

            tracker.step(f"AI ranking {len(matched)} match(es) with {llm.provider}")
            ranked = llm.analyze(matched, query, history=history)

            tracker.step(f"Generating signals for {len(matched)} stock(s)")
            signals = signal_gen.generate(matched)

            tracker.done()
            table = format_signal_table(ranked, signals, stock_cache)
            detail = format_signal_detail(signals)
            print(table)
            print(detail)
            print()

            # Save to history (summarized)
            tickers = [r.get("ticker", "") for r in ranked[:5]]
            history.append({
                "role": "assistant",
                "content": f"Showed {len(matched)} results: {', '.join(tickers)}. "
                           f"Signals: {', '.join(s.get('ticker','')+'='+s.get('signal','') for s in signals[:5])}"
            })
            # Keep history bounded
            if len(history) > 20:
                history = history[-16:]

        except Exception as e:
            tracker.done()
            print(f"Error: {e}\n")


def _ensure_cache(stock_cache, universe, tracker=None):
    """Load stock cache if not already loaded."""
    if stock_cache is None:
        if tracker:
            tracker.step(f"Fetching data for {len(universe)} stocks (cached after first run)")
        stocks = get_multiple_stocks(universe, refresh=False)
        return {s["ticker"]: s for s in stocks}
    else:
        if tracker:
            tracker.step("Using cached stock data")
    return stock_cache


def _handle_command(query, llm, signal_gen, stock_cache, universe, refresh):
    """Handle direct commands. Returns response string, or None if not a command."""
    q = query.strip()
    ql = q.lower()

    # ── Watchlist ──
    m = re.match(r"^watch\s+(\S+)$", ql)
    if m:
        return user.add_to_watchlist(m.group(1))

    m = re.match(r"^unwatch\s+(\S+)$", ql)
    if m:
        return user.remove_from_watchlist(m.group(1))

    if ql == "watchlist":
        return user.format_watchlist()

    if ql in ("watchlist signals", "watchlist signal"):
        wl = user.get_watchlist()
        if not wl:
            return "Your watchlist is empty. Use 'watch TICKER' to add stocks."
        if stock_cache is None:
            return "__CACHE_NEEDED__"
        matched = [stock_cache[t] for t in wl if t in stock_cache]
        if not matched:
            return "No data found for your watchlist stocks."
        tracker = StepTracker()
        tracker.step(f"Generating signals for {len(matched)} watchlist stock(s)")
        signals = signal_gen.generate(matched)
        tracker.done()
        return format_signal_detail(signals)

    # ── Portfolio ──
    m = re.match(r"^buy\s+([\d.]+)\s+(\S+)\s+at\s+([\d.]+)$", ql)
    if m:
        qty, ticker, price = float(m.group(1)), m.group(2), float(m.group(3))
        return user.add_holding(ticker, qty, price)

    m = re.match(r"^sell\s+(\S+)$", ql)
    if m:
        return user.remove_holding(m.group(1))

    if ql == "portfolio":
        if stock_cache is None:
            return "__CACHE_NEEDED__"
        return user.format_portfolio(stock_cache)

    # ── Preferences ──
    m = re.match(r"^prefer\s+sectors?\s+(.+)$", ql)
    if m:
        return user.set_preference("sectors", m.group(1))

    m = re.match(r"^prefer\s+(max_pe|max_debt_to_equity|min_dividend_yield)\s+([\d.]+)$", ql)
    if m:
        return user.set_preference(m.group(1), m.group(2))

    if ql == "prefer clear":
        return user.clear_preferences()

    if ql in ("preferences", "prefs"):
        return user.format_preferences()

    return None
