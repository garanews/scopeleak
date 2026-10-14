"""Agreement + client message -> classified requests with references."""
from core import evidence, llm

# v3.1 changes the validator only (included + excluding line -> ambiguous);
# the prompt and schema are identical to v3.
PROMPT_VERSION = "v3.1-conflict-check"

SYSTEM = """You help freelancers spot scope creep.
You receive the ORIGINAL AGREEMENT between a freelancer and a client, with numbered lines (L1, L2, ...), and a NEW MESSAGE from the client.

1. Identify every distinct request the client makes in the message. Merge repeated mentions of the same thing into one request.
2. For each request, look for two kinds of agreement lines:
   - "covering_lines": lines that include the request. Examples: it is a listed deliverable, it follows the process the agreement describes, it is a revision within the stated number of rounds, it is a fix within the stated support period.
   - "excluding_lines": lines that explicitly exclude the request, or that set a limit the request exceeds (number of pages, concepts, revision rounds, support period...).
   Write lines as they appear, e.g. ["L7", "L18"]. Either list may be empty.
3. Then decide:
   - "included": a covering line applies and no excluding line does.
   - "extra": an excluding line applies.
   - "ambiguous": no line clearly covers or excludes it. Something the agreement simply does not mention is ambiguous, not extra.
   Do not mark a request as extra just because it asks for a change: changes inside the agreed limits are included.
4. "message_quote": copy the exact words from the message that contain the request.
5. Never estimate hours or prices.
"""

# Property order: the verdict comes last, after reasoning and references.
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
                    "reasoning": {"type": "string"},
                    # Strings, not integers: the model wants to write "L18" as it
                    # appears in the prompt, and an integer-only grammar made it
                    # emit an empty list instead (v2).
                    # Two lists, not one: asked for "lines that justify the
                    # verdict", the model never cited the exclusion clause for
                    # extra requests (v2.1, v2.2).
                    "covering_lines": {"type": "array", "items": {"type": "string"}},
                    "excluding_lines": {"type": "array", "items": {"type": "string"}},
                    "verdict": {"type": "string", "enum": ["included", "extra", "ambiguous"]},
                },
                "required": ["summary", "message_quote", "reasoning", "covering_lines",
                             "excluding_lines", "verdict"],
            },
        }
    },
    "required": ["requests"],
}


def classify(agreement: str, message: str, config: dict | None = None) -> list[dict]:
    config = config or llm.load_config()
    lines = evidence.number_lines(agreement)
    result = llm.chat_json(
        config,
        [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"ORIGINAL AGREEMENT:\n{evidence.render_numbered(lines)}\n\n"
                                        f"NEW MESSAGE:\n{message}"},
        ],
        SCHEMA,
    )
    return [evidence.validate(item, lines, message) for item in result.get("requests", [])]
