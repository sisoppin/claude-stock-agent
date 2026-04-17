from dataclasses import dataclass
from typing import Optional


@dataclass
class FilterCriteria:
    max_pe: Optional[float] = None
    min_pe: Optional[float] = None
    min_market_cap_cr: Optional[float] = None   # in crores (1 crore = 1e7 rupees)
    max_market_cap_cr: Optional[float] = None
    min_dividend_yield: Optional[float] = None  # percentage (e.g., 1.5 for 1.5%)
    max_debt_to_equity: Optional[float] = None
    max_rsi: Optional[float] = None
    min_rsi: Optional[float] = None
    above_ma50: Optional[bool] = None
    above_ma200: Optional[bool] = None
    macd_bullish: Optional[bool] = None
    sector: Optional[str] = None


def screen_stocks(stocks: list, criteria: FilterCriteria) -> list:
    """Return stocks that satisfy all specified criteria. None fields are skipped."""
    return [s for s in stocks if _matches(s, criteria)]


def _matches(stock: dict, criteria: FilterCriteria) -> bool:
    pe = stock.get("pe_ratio")
    market_cap = stock.get("market_cap")
    market_cap_cr = (market_cap / 1e7) if market_cap else None
    price = stock.get("price")

    checks = [
        criteria.max_pe is None or (pe is not None and pe <= criteria.max_pe),
        criteria.min_pe is None or (pe is not None and pe >= criteria.min_pe),
        criteria.min_market_cap_cr is None or (market_cap_cr is not None and market_cap_cr >= criteria.min_market_cap_cr),
        criteria.max_market_cap_cr is None or (market_cap_cr is not None and market_cap_cr <= criteria.max_market_cap_cr),
        criteria.min_dividend_yield is None or stock.get("dividend_yield", 0) >= criteria.min_dividend_yield,
        criteria.max_debt_to_equity is None or (stock.get("debt_to_equity") is not None and stock["debt_to_equity"] <= criteria.max_debt_to_equity),
        criteria.max_rsi is None or (stock.get("rsi") is not None and stock["rsi"] <= criteria.max_rsi),
        criteria.min_rsi is None or (stock.get("rsi") is not None and stock["rsi"] >= criteria.min_rsi),
        criteria.above_ma50 is None or (price and stock.get("ma50") and (price > stock["ma50"]) == criteria.above_ma50),
        criteria.above_ma200 is None or (price and stock.get("ma200") and (price > stock["ma200"]) == criteria.above_ma200),
        criteria.macd_bullish is None or stock.get("macd_bullish") == criteria.macd_bullish,
        criteria.sector is None or stock.get("sector", "").lower() == criteria.sector.lower(),
    ]
    return all(checks)
