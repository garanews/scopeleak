"""Reference integrity validation.

The model may reason however it likes, but every reference it hands back must
point at something that exists: agreement clauses are cited by line number and
the client's request by an exact quote. This module checks that the
references are real. It cannot tell whether they *support* the verdict — that
part stays probabilistic, and the freelancer has the final word.
"""
import re
import unicodedata

_QUOTE_CHARS = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", " ": " ",
})


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_QUOTE_CHARS).lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .,;:\"'")


def find_quote(quote: str, source: str) -> bool:
    q = normalize(quote)
    return len(q) >= 8 and q in normalize(source)


def number_lines(agreement: str) -> list[str]:
    """Non-empty lines of the agreement; line N is lines[N - 1]."""
    return [line.strip() for line in agreement.splitlines() if line.strip()]


def render_numbered(lines: list[str]) -> str:
    return "\n".join(f"L{i}: {line}" for i, line in enumerate(lines, 1))


def resolve_lines(refs: list, lines: list[str]) -> list[dict]:
    cited = []
    for ref in refs:
        match = re.fullmatch(r"\s*L?(\d+)\s*", str(ref), re.I)
        n = int(match.group(1)) if match else None
        valid = n is not None and 1 <= n <= len(lines)
        cited.append({"line": ref, "valid": valid, "text": lines[n - 1] if valid else None})
    return cited


# The kind of reference each verdict needs: `included` must cite a line that
# covers the request, `extra` a line that excludes it or sets a limit it
# exceeds. Something merely missing from the agreement can never be `extra`.
REQUIRED_LINES = {"included": "covering_lines", "extra": "excluding_lines"}


def validate(item: dict, lines: list[str], message: str) -> dict:
    """Annotate one classified request with reference checks.

    A verdict of `included` or `extra` needs a real quote from the message and
    at least one existing agreement line of the matching kind; otherwise it is
    downgraded to `ambiguous`. The model's original verdict is kept for
    evaluation.
    """
    covering = resolve_lines(item.get("covering_lines", []), lines)
    excluding = resolve_lines(item.get("excluding_lines", []), lines)
    message_ok = find_quote(item.get("message_quote", ""), message)

    verdict = item.get("verdict", "ambiguous")
    downgraded = False
    if verdict in REQUIRED_LINES:
        cited = covering if verdict == "included" else excluding
        downgraded = not (message_ok and any(c["valid"] for c in cited))

    return {
        **item,
        "model_verdict": verdict,
        "verdict": "ambiguous" if downgraded else verdict,
        "evidence": {
            "message_quote_found": message_ok,
            "covering_lines": covering,
            "excluding_lines": excluding,
            "downgraded": downgraded,
        },
    }
