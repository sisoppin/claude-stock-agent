import json
import pytest
from unittest.mock import patch, MagicMock
from agent.llm import LLMProvider, get_provider

SAMPLE_STOCKS = [
    {"ticker": "INFY", "pe_ratio": 12.4, "rsi": 36.2, "price": 1842.0, "sector": "Technology"},
    {"ticker": "WIPRO", "pe_ratio": 11.1, "rsi": 38.9, "price": 498.0, "sector": "Technology"},
]

SAMPLE_RANKED = [
    {"ticker": "INFY", "rank": 1, "score": 87,
     "reason": "Strong fundamentals with low P/E relative to sector, oversold RSI signals entry opportunity."},
    {"ticker": "WIPRO", "rank": 2, "score": 74,
     "reason": "Undervalued vs sector peers with consistent dividend history."},
]

SAMPLE_CRITERIA = {"max_pe": 15, "max_rsi": 40, "sector": "Technology"}


@patch("agent.llm.Anthropic")
def test_analyze_claude_returns_ranked_list(mock_anthropic):
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content[0].text = json.dumps(SAMPLE_RANKED)
    mock_anthropic.return_value = mock_client

    llm = LLMProvider("claude", {})
    result = llm.analyze(SAMPLE_STOCKS, "low P/E IT stocks")

    assert len(result) == 2
    assert result[0]["ticker"] == "INFY"
    assert result[0]["rank"] == 1
    assert result[0]["score"] == 87
    assert "reason" in result[0]


@patch("agent.llm.OpenAI")
def test_analyze_openai_returns_ranked_list(mock_openai):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices[0].message.content = json.dumps(SAMPLE_RANKED)
    mock_openai.return_value = mock_client

    llm = LLMProvider("openai", {})
    result = llm.analyze(SAMPLE_STOCKS, "low P/E IT stocks")

    assert len(result) == 2
    assert result[0]["ticker"] == "INFY"


@patch("agent.llm.requests.post")
def test_analyze_perplexity_returns_ranked_list(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps(SAMPLE_RANKED)}}]
    }
    mock_response.raise_for_status = lambda: None
    mock_post.return_value = mock_response

    llm = LLMProvider("perplexity", {})
    result = llm.analyze(SAMPLE_STOCKS, "low P/E IT stocks")

    assert len(result) == 2
    assert result[1]["ticker"] == "WIPRO"


@patch("agent.llm.requests.post")
def test_analyze_ollama_returns_ranked_list(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {"content": json.dumps(SAMPLE_RANKED)}
    }
    mock_response.raise_for_status = lambda: None
    mock_post.return_value = mock_response

    llm = LLMProvider("ollama", {"ollama_url": "http://localhost:11434", "ollama_model": "llama3"})
    result = llm.analyze(SAMPLE_STOCKS, "low P/E IT stocks")

    assert len(result) == 2


@patch("agent.llm.Anthropic")
def test_analyze_handles_markdown_wrapped_json(mock_anthropic):
    wrapped = f"```json\n{json.dumps(SAMPLE_RANKED)}\n```"
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content[0].text = wrapped
    mock_anthropic.return_value = mock_client

    llm = LLMProvider("claude", {})
    result = llm.analyze(SAMPLE_STOCKS, "query")

    assert len(result) == 2


@patch("agent.llm.Anthropic")
def test_parse_query_returns_filter_dict(mock_anthropic):
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content[0].text = json.dumps(SAMPLE_CRITERIA)
    mock_anthropic.return_value = mock_client

    llm = LLMProvider("claude", {})
    result = llm.parse_query("IT stocks with P/E below 15 and RSI below 40")

    assert result["max_pe"] == 15
    assert result["max_rsi"] == 40
    assert result["sector"] == "Technology"


def test_get_provider_returns_llm_provider():
    provider = get_provider("claude", {})
    assert isinstance(provider, LLMProvider)
    assert provider.provider == "claude"


def test_unknown_provider_raises_value_error():
    llm = LLMProvider("unknown_provider", {})
    with pytest.raises(ValueError, match="Unknown provider: unknown_provider"):
        llm.analyze([], "query")
