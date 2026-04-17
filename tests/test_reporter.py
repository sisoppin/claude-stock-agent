from agent.reporter import format_report

RANKED = [
    {"ticker": "INFY", "rank": 1, "score": 87,
     "reason": "Strong fundamentals with low P/E relative to sector."},
    {"ticker": "WIPRO", "rank": 2, "score": 74,
     "reason": "Undervalued vs sector peers with consistent dividend."},
]

STOCK_DATA = {
    "INFY": {"pe_ratio": 12.4, "rsi": 36.2, "price": 1842.0},
    "WIPRO": {"pe_ratio": 11.1, "rsi": 38.9, "price": 498.0},
}


def test_format_report_contains_all_tickers():
    report = format_report(RANKED, STOCK_DATA)
    assert "INFY" in report
    assert "WIPRO" in report


def test_format_report_contains_rupee_symbol():
    report = format_report(RANKED, STOCK_DATA)
    assert "₹" in report


def test_format_report_ranked_order():
    report = format_report(RANKED, STOCK_DATA)
    assert report.find("INFY") < report.find("WIPRO")


def test_format_report_contains_scores():
    report = format_report(RANKED, STOCK_DATA)
    assert "87" in report
    assert "74" in report


def test_format_report_contains_pe_and_rsi():
    report = format_report(RANKED, STOCK_DATA)
    assert "12.4" in report
    assert "36.2" in report


def test_format_report_empty_list():
    report = format_report([], {})
    assert "No stocks matched" in report


def test_format_report_handles_missing_stock_data():
    # ranked contains tickers not in stock_data — should not crash
    report = format_report(RANKED, {})
    assert "INFY" in report
    assert "WIPRO" in report


# --- Signal reporter tests ---

RANKED_SIG = [
    {"ticker": "INFY", "rank": 1, "score": 87, "reason": "Strong fundamentals."},
    {"ticker": "WIPRO", "rank": 2, "score": 74, "reason": "Undervalued vs peers."},
]
SIGNALS = [
    {
        "ticker": "INFY", "signal": "BUY", "confidence": 82,
        "entry_zone": "₹1,800–₹1,850", "stop_loss": "₹1,680",
        "reasoning": "RSI oversold, above 200 DMA, zero debt.",
    },
    {
        "ticker": "WIPRO", "signal": "HOLD", "confidence": 61,
        "entry_zone": "₹490–₹505", "stop_loss": "₹460",
        "reasoning": "Neutral momentum, awaiting MACD confirmation.",
    },
]
STOCK_DATA_SIG = {
    "INFY": {"pe_ratio": 12.4, "rsi": 36.2, "price": 1842.0},
    "WIPRO": {"pe_ratio": 11.1, "rsi": 38.9, "price": 498.0},
}


# format_signal_table tests
def test_signal_table_contains_signal_column():
    from agent.reporter import format_signal_table
    report = format_signal_table(RANKED_SIG, SIGNALS, STOCK_DATA_SIG)
    assert "BUY" in report
    assert "HOLD" in report


def test_signal_table_contains_confidence():
    from agent.reporter import format_signal_table
    report = format_signal_table(RANKED_SIG, SIGNALS, STOCK_DATA_SIG)
    assert "82" in report
    assert "61" in report


def test_signal_table_contains_tickers():
    from agent.reporter import format_signal_table
    report = format_signal_table(RANKED_SIG, SIGNALS, STOCK_DATA_SIG)
    assert "INFY" in report
    assert "WIPRO" in report


def test_signal_table_contains_rupee_symbol():
    from agent.reporter import format_signal_table
    report = format_signal_table(RANKED_SIG, SIGNALS, STOCK_DATA_SIG)
    assert "₹" in report


def test_signal_table_empty_returns_no_match_message():
    from agent.reporter import format_signal_table
    report = format_signal_table([], [], {})
    assert "No stocks matched" in report


# format_signal_detail tests
def test_signal_detail_contains_entry_zone():
    from agent.reporter import format_signal_detail
    detail = format_signal_detail(SIGNALS)
    assert "₹1,800" in detail
    assert "₹490" in detail


def test_signal_detail_contains_stop_loss():
    from agent.reporter import format_signal_detail
    detail = format_signal_detail(SIGNALS)
    assert "₹1,680" in detail
    assert "₹460" in detail


def test_signal_detail_contains_ticker_and_signal():
    from agent.reporter import format_signal_detail
    detail = format_signal_detail(SIGNALS)
    assert "INFY" in detail
    assert "BUY" in detail
    assert "WIPRO" in detail
    assert "HOLD" in detail


def test_signal_detail_empty_returns_empty_string():
    from agent.reporter import format_signal_detail
    assert format_signal_detail([]) == ""


# format_batch_signal_report tests
def test_batch_report_contains_all_tickers():
    from agent.reporter import format_batch_signal_report
    report = format_batch_signal_report(SIGNALS, STOCK_DATA_SIG, "2026-04-17", "claude")
    assert "INFY" in report
    assert "WIPRO" in report


def test_batch_report_contains_date_and_provider():
    from agent.reporter import format_batch_signal_report
    report = format_batch_signal_report(SIGNALS, STOCK_DATA_SIG, "2026-04-17", "claude")
    assert "2026-04-17" in report
    assert "claude" in report


def test_batch_report_contains_entry_and_stop():
    from agent.reporter import format_batch_signal_report
    report = format_batch_signal_report(SIGNALS, STOCK_DATA_SIG, "2026-04-17", "claude")
    assert "₹1,800" in report
    assert "₹1,680" in report
