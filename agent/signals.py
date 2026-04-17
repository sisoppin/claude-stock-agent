import json
from agent.llm import LLMProvider

SIGNAL_SYSTEM_PROMPT = """You are a professional stock market analyst specializing in Indian equities (NSE).
You receive stock data including both technical indicators and fundamental metrics.
For each stock, generate a trading signal based on ALL available data.

Technical signals to consider:
- RSI < 40: oversold (bullish), RSI > 70: overbought (bearish)
- Price above 200 DMA: long-term uptrend, below: downtrend
- Price above 50 DMA: short-term momentum positive
- MACD bullish (True): momentum turning positive

Fundamental signals to consider:
- Low P/E vs sector: undervalued (bullish)
- High debt-to-equity (>1): financial risk (bearish)
- Dividend yield > 1%: income support (neutral to bullish)

For each stock output:
1. signal: BUY (setup is favourable), SELL (deteriorating), or HOLD (neutral/unclear)
2. confidence: 0-100 reflecting signal strength
3. entry_zone: suggested ₹ price range to enter (near current support level)
4. stop_loss: ₹ price where the thesis is invalidated
5. reasoning: 2-3 sentences combining technical + fundamental factors, reference ₹ values

Return ONLY valid JSON — no markdown, no explanation. One object per stock, always an array:
[
  {"ticker": "X", "signal": "BUY", "confidence": 82, "entry_zone": "₹1,800–₹1,850",
   "stop_loss": "₹1,680", "reasoning": "..."},
  {"ticker": "Y", "signal": "SELL", "confidence": 70, "entry_zone": "N/A",
   "stop_loss": "₹500", "reasoning": "..."}
]
(confidence is an integer 0-100)"""


class SignalGenerator:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def generate(self, stocks: list) -> list:
        """Generate BUY/SELL/HOLD signals for a list of stocks using LLM analysis."""
        if not stocks:
            return []
        prompt = (
            f"Generate trading signals for these {len(stocks)} NSE stocks:\n"
            f"{json.dumps(stocks, indent=2, default=str)}"
        )
        text = self.llm._complete(prompt, SIGNAL_SYSTEM_PROMPT)
        return self.llm._extract_json(text)
