import math


def format_report(ranked_stocks: list, stock_data: dict) -> str:
    """Render ranked stocks as a terminal table with ₹ values."""
    if not ranked_stocks:
        return "No stocks matched your criteria. Try relaxing the filters."

    header = f"\n{'RANK':<6} {'TICKER':<12} {'SCORE':<8} {'P/E':<8} {'RSI':<8} {'PRICE (₹)':<14} REASON"
    divider = "-" * 95
    lines = [header, divider]

    for item in sorted(ranked_stocks, key=lambda x: x["rank"]):
        ticker = item.get("ticker", "")
        data = stock_data.get(ticker, {})

        pe = data.get("pe_ratio")
        rsi = data.get("rsi")
        price = data.get("price", 0)

        pe_str = f"{pe:.1f}" if isinstance(pe, (int, float)) and not math.isnan(pe) else "N/A"
        rsi_str = f"{rsi:.1f}" if isinstance(rsi, (int, float)) and not math.isnan(rsi) else "N/A"
        price_str = f"₹{price:,.0f}" if price is not None else "N/A"
        reason = item.get("reason", "")[:120]

        lines.append(
            f"{item['rank']:<6} {ticker:<12} {item['score']:<8} {pe_str:<8} {rsi_str:<8} {price_str:<14} {reason}"
        )

    return "\n".join(lines)


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
