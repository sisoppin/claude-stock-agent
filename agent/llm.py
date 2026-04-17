import json
import os
import re
import requests
from anthropic import Anthropic
from openai import OpenAI

ANALYZE_SYSTEM_PROMPT = """You are a stock market analyst specializing in Indian equities (NSE).
You receive a list of stocks that passed screening filters, with their metrics.
Your job:
1. Rank them from best to worst investment candidate (1 = best)
2. Assign a composite score 0-100
3. Write 2-3 sentences of plain-English reasoning per stock (reference ₹ values)

Return ONLY valid JSON — no markdown, no explanation:
[{"ticker": "X", "rank": 1, "score": 87, "reason": "..."}]"""

PARSE_SYSTEM_PROMPT = """You are a JSON parser for stock screening queries.
Return ONLY valid JSON with these optional keys (null for unspecified):
{"max_pe": null, "min_pe": null, "min_market_cap_cr": null, "max_market_cap_cr": null,
 "min_dividend_yield": null, "max_debt_to_equity": null, "max_rsi": null, "min_rsi": null,
 "above_ma50": null, "above_ma200": null, "macd_bullish": null, "sector": null}

Rules:
- "large-cap" → min_market_cap_cr: 20000
- "mid-cap"   → min_market_cap_cr: 5000, max_market_cap_cr: 20000
- "small-cap" → max_market_cap_cr: 5000
- "IT sector" or "technology" → sector: "Technology"
- "P/E below 15" → max_pe: 15
- "RSI below 40" → max_rsi: 40
- "above 200 DMA" → above_ma200: true
- "MACD bullish" → macd_bullish: true"""


class LLMProvider:
    def __init__(self, provider: str, config: dict):
        self.provider = provider
        self.config = config
        self._client = None
        if provider == "claude":
            self._client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        elif provider == "openai":
            self._client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

    def analyze(self, stocks: list, query: str) -> list:
        """Rank and explain screened stocks. Returns list of dicts with rank/score/reason."""
        prompt = f"User query: {query}\n\nStocks:\n{json.dumps(stocks, indent=2, default=str)}"
        text = self._complete(prompt, ANALYZE_SYSTEM_PROMPT)
        return self._extract_json(text)

    def parse_query(self, query: str) -> dict:
        """Translate natural language query into FilterCriteria field dict."""
        prompt = f'Parse this stock screening query: "{query}"'
        text = self._complete(prompt, PARSE_SYSTEM_PROMPT)
        return self._extract_json(text)

    def _complete(self, prompt: str, system: str) -> str:
        if self.provider == "claude":
            return self._call_claude(prompt, system)
        elif self.provider == "openai":
            return self._call_openai(prompt, system)
        elif self.provider == "perplexity":
            return self._call_perplexity(prompt, system)
        elif self.provider == "ollama":
            return self._call_ollama(prompt, system)
        raise ValueError(f"Unknown provider: {self.provider}")

    def _extract_json(self, text: str):
        """Parse JSON from LLM response, stripping markdown code blocks if present."""
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            text = match.group(1)
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM returned non-JSON: {text[:200]!r}") from exc

    def _call_claude(self, prompt: str, system: str) -> str:
        response = self._client.messages.create(
            model=self.config.get("claude_model", "claude-sonnet-4-6"),
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def _call_openai(self, prompt: str, system: str) -> str:
        response = self._client.chat.completions.create(
            model=self.config.get("openai_model", "gpt-4o"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content

    def _call_perplexity(self, prompt: str, system: str) -> str:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {os.environ.get('PERPLEXITY_API_KEY', '')}"},
            json={
                "model": self.config.get("perplexity_model", "sonar-pro"),
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def _call_ollama(self, prompt: str, system: str) -> str:
        url = self.config.get("ollama_url", "http://localhost:11434")
        model = self.config.get("ollama_model", "llama3")
        timeout = self.config.get("ollama_timeout", 300)
        response = requests.post(
            f"{url}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]


def get_provider(name: str, config: dict) -> LLMProvider:
    return LLMProvider(provider=name, config=config)
