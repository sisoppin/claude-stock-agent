import json
from unittest.mock import MagicMock
from agent.signals import SignalGenerator

SAMPLE_STOCKS = [
    {
        "ticker": "INFY", "pe_ratio": 12.4, "rsi": 36.2, "price": 1842.0,
        "macd_bullish": True, "ma50": 1800.0, "ma200": 1750.0,
        "dividend_yield": 2.5, "debt_to_equity": 0.0, "sector": "Technology",
    },
    {
        "ticker": "RELIANCE", "pe_ratio": 24.5, "rsi": 62.0, "price": 2800.0,
        "macd_bullish": False, "ma50": 2750.0, "ma200": 2600.0,
        "dividend_yield": 0.5, "debt_to_equity": 35.2, "sector": "Energy",
    },
    {
        "ticker": "TATASTEEL", "pe_ratio": 8.1, "rsi": 74.3, "price": 158.0,
        "macd_bullish": False, "ma50": 162.0, "ma200": 145.0,
        "dividend_yield": 1.2, "debt_to_equity": 1.8, "sector": "Metals",
    },
]

SAMPLE_SIGNALS = [
    {
        "ticker": "INFY", "signal": "BUY", "confidence": 82,
        "entry_zone": "₹1,800–₹1,850", "stop_loss": "₹1,680",
        "reasoning": "RSI oversold at 36 with price above 200 DMA and zero debt.",
    },
    {
        "ticker": "RELIANCE", "signal": "HOLD", "confidence": 55,
        "entry_zone": "₹2,750–₹2,810", "stop_loss": "₹2,580",
        "reasoning": "Neutral momentum; awaiting MACD confirmation above signal line.",
    },
    {
        "ticker": "TATASTEEL", "signal": "SELL", "confidence": 71,
        "entry_zone": "N/A", "stop_loss": "₹140",
        "reasoning": "RSI overbought at 74, breaking below 50 DMA with high D/E ratio.",
    },
]


def _mock_llm(response):
    llm = MagicMock()
    llm._complete.return_value = json.dumps(response)
    llm._extract_json.return_value = response
    return llm


def test_generate_returns_signal_list():
    gen = SignalGenerator(_mock_llm(SAMPLE_SIGNALS))
    result = gen.generate(SAMPLE_STOCKS)
    assert len(result) == 3
    assert result[0]["ticker"] == "INFY"
    assert result[0]["signal"] == "BUY"
    assert result[0]["confidence"] == 82
    assert "entry_zone" in result[0]
    assert "stop_loss" in result[0]
    assert "reasoning" in result[0]


def test_generate_empty_stocks_returns_empty_without_calling_llm():
    llm = _mock_llm([])
    gen = SignalGenerator(llm)
    result = gen.generate([])
    assert result == []
    llm._complete.assert_not_called()


def test_generate_calls_llm_with_ticker_in_prompt():
    llm = _mock_llm(SAMPLE_SIGNALS)
    gen = SignalGenerator(llm)
    gen.generate(SAMPLE_STOCKS)
    llm._complete.assert_called_once()
    prompt = llm._complete.call_args[0][0]
    assert "INFY" in prompt
    assert "RELIANCE" in prompt


def test_generate_signal_values_are_valid():
    gen = SignalGenerator(_mock_llm(SAMPLE_SIGNALS))
    result = gen.generate(SAMPLE_STOCKS)
    for sig in result:
        assert sig["signal"] in ("BUY", "SELL", "HOLD")
        assert 0 <= sig["confidence"] <= 100


def test_generate_uses_signal_system_prompt():
    from agent.signals import SIGNAL_SYSTEM_PROMPT
    from unittest.mock import ANY
    assert "BUY" in SIGNAL_SYSTEM_PROMPT
    assert "SELL" in SIGNAL_SYSTEM_PROMPT
    assert "HOLD" in SIGNAL_SYSTEM_PROMPT
    assert "stop" in SIGNAL_SYSTEM_PROMPT.lower()
    assert "entry" in SIGNAL_SYSTEM_PROMPT.lower()
    # Verify it is actually passed to _complete as the system argument
    llm = _mock_llm(SAMPLE_SIGNALS)
    gen = SignalGenerator(llm)
    gen.generate(SAMPLE_STOCKS)
    llm._complete.assert_called_once_with(ANY, SIGNAL_SYSTEM_PROMPT)
