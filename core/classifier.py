"""Agreement + client message -> classified requests with citations."""
from core import evidence, llm

PROMPT_VERSION = "v1"

SYSTEM = """You help freelancers spot scope creep.
You receive the ORIGINAL AGREEMENT between a freelancer and a client, and a NEW MESSAGE from the client.

1. Identify every distinct request the client makes in the message. Merge repeated mentions of the same thing into one request.
2. For each request decide:
   - "included": the agreement clearly covers it.
   - "extra": the agreement clearly excludes it, or it clearly exceeds a stated limit (number of pages, revision rounds, support period...).
   - "ambiguous": the agreement neither clearly covers nor clearly excludes it.
3. Support each verdict with quotes:
   - "message_quote": copy the exact words from the message that contain the request.
   - "agreement_quotes": copy one or more exact sentences or phrases from the agreement that justify the verdict.
   Copy quotes character by character. Do not paraphrase. If no part of the agreement applies, return an empty list and use "ambiguous".
4. Never estimate hours or prices.
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "requests": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "message_quote": {"type": "string"},
                    "verdict": {"type": "string", "enum": ["included", "extra", "ambiguous"]},
                    "agreement_quotes": {"type": "array", "items": {"type": "string"}},
                    "reasoning": {"type": "string"},
                },
                "required": ["summary", "message_quote", "verdict", "agreement_quotes", "reasoning"],
            },
        }
    },
    "required": ["requests"],
}


def classify(agreement: str, message: str, config: dict | None = None) -> list[dict]:
    config = config or llm.load_config()
    result = llm.chat_json(
        config,
        [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"ORIGINAL AGREEMENT:\n{agreement}\n\nNEW MESSAGE:\n{message}"},
        ],
        SCHEMA,
    )
    return [evidence.validate(item, agreement, message) for item in result.get("requests", [])]
