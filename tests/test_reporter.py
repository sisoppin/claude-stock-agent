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
