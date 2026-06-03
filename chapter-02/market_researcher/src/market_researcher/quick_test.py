"""Quick smoke test for the OpenAI Responses API tool-calling surface.

The previous version of this file hardcoded a real OpenAI API key in source
and committed it to git. That key has been revoked and the example now reads
the key from the environment, matching the pattern used in every other
chapter of the book.

Run with:

    export OPENAI_API_KEY=sk-...
    uv run python src/market_researcher/quick_test.py
"""
import os

from openai import OpenAI


def _require_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise SystemExit(
            "OPENAI_API_KEY is not set. Export it (or add it to .env) and retry."
        )
    return key


client = OpenAI(api_key=_require_api_key())

tools = [{
    "type": "function",
    "name": "get_report",
    "description": "Get the financial report for a given year.",
    "parameters": {
        "type": "object",
        "properties": {
            "year": {"type": "number"},
        },
        "required": ["year"],
        "additionalProperties": False
    },
    "strict": True
}]

input_messages = [
    {
        "role": "user",
        "content": "How much revenue did we make in 2024?"
    }
]

response = client.responses.create(
    model="gpt-5",
    input=input_messages,
    tools=tools,
)

print([item.model_dump_json() for item in response.output])
