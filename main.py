import argparse

import yaml
from dotenv import load_dotenv

from agent.llm import get_provider
from agent.chat import run_chat


def main():
    load_dotenv()

    with open("config/config.yaml") as f:
        config = yaml.safe_load(f)

    parser = argparse.ArgumentParser(
        description="Stock Market AI Agent — NSE/BSE Screener"
    )
    parser.add_argument(
        "--provider",
        choices=["claude", "openai", "perplexity", "ollama"],
        default=config.get("provider", "claude"),
        help="LLM provider (default: from config.yaml)",
    )
    args = parser.parse_args()

    config["provider"] = args.provider
    llm = get_provider(args.provider, config)
    run_chat(llm)


if __name__ == "__main__":
    main()
