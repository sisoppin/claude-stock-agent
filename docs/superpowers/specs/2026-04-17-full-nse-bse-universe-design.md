# Full NSE + BSE Universe Expansion

**Date:** 2026-04-17
**Status:** Approved

## Goal

Replace the hardcoded 45-stock `NSE_UNIVERSE` with a dynamically fetched list of all actively listed equities on both NSE (~2,000 symbols) and BSE (~5,000 symbols), with daily caching and a `--refresh` flag.

## Architecture

### New function: `fetch_universe(refresh=False) -> list[str]`

Added to `agent/data.py`.

1. Check `cache/universe.json` — if it exists, age < 24h, and `refresh=False`, return the cached list.
2. Otherwise, fetch two public CSVs (both require `User-Agent` header):
   - **NSE:** `https://archives.nseindia.com/content/equities/EQUITY_L.csv` → column `SYMBOL` → append `.NS`
   - **BSE:** `https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?segment=Equity&status=Active` → field `scrip_id` → append `.BO`
3. Deduplicate: any symbol present in both NSE and BSE lists → keep `.NS` only (better yfinance coverage).
4. Write result + ISO timestamp to `cache/universe.json`.
5. Fallback: if both fetches fail, warn and return the existing `NSE_UNIVERSE` constant.

### Refactored: `get_multiple_stocks(tickers, refresh=False) -> list[dict]`

- **Cache:** `cache/stocks_YYYY-MM-DD.json`. If today's file exists and `refresh=False`, load and return immediately.
- **Parallel fetch:** Replace sequential loop with `ThreadPoolExecutor(max_workers=20)`. Each worker calls existing `get_stock_data()`. Failed tickers (delisted, no data) return `None` and are silently skipped.
- **Cache write:** After fetch completes, write all results atomically to `cache/stocks_YYYY-MM-DD.json`.
- Old daily cache files are not auto-deleted (manual cleanup).

### `main.py`

- Add `--refresh` flag to argparse (store_true).
- Import `fetch_universe` instead of `NSE_UNIVERSE`.
- Pass `refresh` into both `fetch_universe()` and `get_multiple_stocks()`.
- Batch signals mode prints real stock count.

### `chat.py`

- Replace `NSE_UNIVERSE` with `fetch_universe(refresh=False)`.
- Pass `refresh=False` to `get_multiple_stocks()` (chat never force-refreshes mid-session).
- In-memory `stock_cache` dict unchanged.

## Data Flow

```
startup
  └─ fetch_universe(refresh)
       ├─ cache/universe.json fresh? → return cached list
       └─ stale/missing → download NSE CSV + BSE JSON
                        → deduplicate → write cache → return list

first scan in session
  └─ get_multiple_stocks(tickers, refresh)
       ├─ cache/stocks_YYYY-MM-DD.json exists? → load from cache
       └─ missing/refresh → ThreadPoolExecutor(20) → get_stock_data() × N
                          → write cache → return list

--refresh flag
  └─ deletes cache/universe.json + cache/stocks_YYYY-MM-DD.json before above
```

## Cache Layout

```
cache/                        ← added to .gitignore
  universe.json               ← {tickers: [...], fetched_at: "2026-04-17T10:00:00"}
  stocks_2026-04-17.json      ← {ticker: {...stock data...}, ...}
  stocks_2026-04-16.json      ← previous day, not auto-deleted
```

## Files Changed

| File | Change |
|------|--------|
| `agent/data.py` | Add `fetch_universe()`, refactor `get_multiple_stocks()` with threadpool + cache |
| `main.py` | Add `--refresh` flag, use `fetch_universe()` |
| `agent/chat.py` | Use `fetch_universe()` |
| `.gitignore` | Add `cache/` |

## Files Unchanged

`agent/screener.py`, `agent/llm.py`, `agent/signals.py`, `agent/reporter.py`

## Error Handling

- NSE/BSE fetch fails → warn + fall back to `NSE_UNIVERSE`
- Individual stock fetch fails → skip silently (unchanged behaviour)
- Cache write fails → log warning, continue (data still in memory)

## Testing

- Unit test `fetch_universe()` with mocked HTTP responses for both NSE and BSE endpoints
- Unit test cache hit path (no HTTP call made when cache is fresh)
- Unit test `--refresh` busts cache
- Unit test parallel fetch still skips failed tickers
- Existing 51 tests must continue to pass
