import json
import pathlib

_USER_FILE = pathlib.Path(__file__).parent.parent / "cache" / "user_profile.json"

_DEFAULT = {
    "watchlist": [],
    "portfolio": [],
    "preferences": {
        "sectors": [],
        "max_pe": None,
        "max_debt_to_equity": None,
        "min_dividend_yield": None,
    },
}


def _load() -> dict:
    _USER_FILE.parent.mkdir(exist_ok=True)
    if _USER_FILE.exists():
        try:
            return json.loads(_USER_FILE.read_text())
        except Exception:
            pass
    return json.loads(json.dumps(_DEFAULT))


def _save(data: dict):
    _USER_FILE.parent.mkdir(exist_ok=True)
    _USER_FILE.write_text(json.dumps(data, indent=2, default=str))


# ── Watchlist ──────────────────────────────────────────────

def get_watchlist() -> list:
    return _load().get("watchlist", [])


def add_to_watchlist(ticker: str) -> str:
    data = _load()
    t = ticker.upper().strip()
    if t in data["watchlist"]:
        return f"{t} is already in your watchlist."
    data["watchlist"].append(t)
    _save(data)
    return f"Added {t} to watchlist. ({len(data['watchlist'])} stocks)"


def remove_from_watchlist(ticker: str) -> str:
    data = _load()
    t = ticker.upper().strip()
    if t not in data["watchlist"]:
        return f"{t} is not in your watchlist."
    data["watchlist"].remove(t)
    _save(data)
    return f"Removed {t} from watchlist."


def format_watchlist() -> str:
    wl = get_watchlist()
    if not wl:
        return "Your watchlist is empty. Use 'watch TICKER' to add stocks."
    return "📋 Your Watchlist: " + ", ".join(wl)


# ── Portfolio ──────────────────────────────────────────────

def get_portfolio() -> list:
    return _load().get("portfolio", [])


def add_holding(ticker: str, qty: float, buy_price: float) -> str:
    data = _load()
    t = ticker.upper().strip()
    for h in data["portfolio"]:
        if h["ticker"] == t:
            old_qty = h["qty"]
            old_cost = h["buy_price"] * old_qty
            new_cost = buy_price * qty
            h["qty"] = old_qty + qty
            h["buy_price"] = round((old_cost + new_cost) / h["qty"], 2)
            _save(data)
            return f"Updated {t}: {h['qty']} shares @ avg ₹{h['buy_price']:,.2f}"
    data["portfolio"].append({"ticker": t, "qty": qty, "buy_price": buy_price})
    _save(data)
    return f"Added {t}: {qty} shares @ ₹{buy_price:,.2f}"


def remove_holding(ticker: str) -> str:
    data = _load()
    t = ticker.upper().strip()
    before = len(data["portfolio"])
    data["portfolio"] = [h for h in data["portfolio"] if h["ticker"] != t]
    if len(data["portfolio"]) == before:
        return f"{t} is not in your portfolio."
    _save(data)
    return f"Removed {t} from portfolio."


def format_portfolio(stock_cache: dict) -> str:
    holdings = get_portfolio()
    if not holdings:
        return "Your portfolio is empty. Use 'buy QTY TICKER at PRICE' to add holdings."
    lines = [
        "\n💼 Your Portfolio",
        f"{'TICKER':<12} {'QTY':<8} {'BUY (₹)':<12} {'CMP (₹)':<12} {'P&L (₹)':<14} {'P&L %':<8}",
        "-" * 70,
    ]
    total_invested = 0
    total_current = 0
    for h in holdings:
        t = h["ticker"]
        qty = h["qty"]
        buy = h["buy_price"]
        data = stock_cache.get(t, {})
        cmp = data.get("price")
        invested = buy * qty
        total_invested += invested
        if cmp is not None:
            current = cmp * qty
            total_current += current
            pnl = current - invested
            pnl_pct = (pnl / invested) * 100 if invested else 0
            sign = "+" if pnl >= 0 else ""
            lines.append(
                f"{t:<12} {qty:<8.0f} ₹{buy:<10,.2f} ₹{cmp:<10,.2f} "
                f"{sign}₹{pnl:<12,.0f} {sign}{pnl_pct:.1f}%"
            )
        else:
            lines.append(f"{t:<12} {qty:<8.0f} ₹{buy:<10,.2f} {'N/A':<12} {'N/A':<14} {'N/A':<8}")
    if total_invested > 0 and total_current > 0:
        total_pnl = total_current - total_invested
        total_pct = (total_pnl / total_invested) * 100
        sign = "+" if total_pnl >= 0 else ""
        lines.append("-" * 70)
        lines.append(
            f"{'TOTAL':<12} {'':<8} ₹{total_invested:<10,.0f} ₹{total_current:<10,.0f} "
            f"{sign}₹{total_pnl:<12,.0f} {sign}{total_pct:.1f}%"
        )
    return "\n".join(lines)


# ── Preferences ────────────────────────────────────────────

def get_preferences() -> dict:
    return _load().get("preferences", _DEFAULT["preferences"])


def set_preference(key: str, value) -> str:
    data = _load()
    prefs = data.get("preferences", {})
    if key == "sectors":
        if isinstance(value, str):
            value = [s.strip() for s in value.split(",")]
        prefs["sectors"] = value
    elif key in ("max_pe", "max_debt_to_equity", "min_dividend_yield"):
        prefs[key] = float(value) if value is not None else None
    else:
        return f"Unknown preference: {key}. Available: sectors, max_pe, max_debt_to_equity, min_dividend_yield"
    data["preferences"] = prefs
    _save(data)
    return f"Preference set: {key} = {value}"


def clear_preferences() -> str:
    data = _load()
    data["preferences"] = json.loads(json.dumps(_DEFAULT["preferences"]))
    _save(data)
    return "All preferences cleared."


def format_preferences() -> str:
    prefs = get_preferences()
    lines = ["⚙️  Your Preferences"]
    sectors = prefs.get("sectors", [])
    lines.append(f"  Sectors        : {', '.join(sectors) if sectors else 'all'}")
    for key in ("max_pe", "max_debt_to_equity", "min_dividend_yield"):
        val = prefs.get(key)
        label = key.replace("_", " ").title()
        lines.append(f"  {label:<16}: {val if val is not None else 'not set'}")
    return "\n".join(lines)
