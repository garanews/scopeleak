"""Agreement + client message -> classified requests with references."""
from core import evidence, llm

PROMPT_VERSION = "v2.2-reasoning-first"

SYSTEM = """You help freelancers spot scope creep.
You receive the ORIGINAL AGREEMENT between a freelancer and a client, with numbered lines (L1, L2, ...), and a NEW MESSAGE from the client.

1. Identify every distinct request the client makes in the message. Merge repeated mentions of the same thing into one request.
2. For each request, first find the agreement lines that are relevant to it, then decide:
   - "included": the agreement covers it. This includes work the agreement lists as a deliverable, following the process the agreement describes, revisions within the stated number of rounds, and fixes within the stated support period.
   - "extra": the agreement explicitly excludes it, or it exceeds a stated limit (number of pages, concepts, revision rounds, support period...), or it is a new deliverable the agreement does not list.
   - "ambiguous": the agreement neither clearly covers nor clearly excludes it.
   Do not mark a request as extra just because it asks for a change: changes inside the agreed limits are included.
3. References:
   - "message_quote": copy the exact words from the message that contain the request.
   - "agreement_lines": the agreement lines that justify the verdict, e.g. ["L7", "L18"]. Use an empty list only if no line applies, and then the verdict must be "ambiguous".
4. Never estimate hours or prices.
"""

# Property order matters: the model reasons first, then lists the lines its
# reasoning relied on, and only then commits to a verdict. With the lines
# before the reasoning, it left them empty for extra requests and found the
# exclusion clause only while reasoning (v2.1).
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
                    # emit an empty list instead.
                    "agreement_lines": {"type": "array", "items": {"type": "string"}},
                    "verdict": {"type": "string", "enum": ["included", "extra", "ambiguous"]},
                },
                "required": ["summary", "message_quote", "reasoning", "agreement_lines", "verdict"],
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
