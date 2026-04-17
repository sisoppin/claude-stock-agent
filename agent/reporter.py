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
