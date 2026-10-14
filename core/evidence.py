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


LONG_LINE = 300

# Sentence boundaries inside a long line: after . ! ? (even with no space, as
# in "build it.Browser" from a PDF copy-paste) when the next sentence starts
# with a capital or a section number; never inside "1.2.4" or "e.g.".
_SENTENCE_BREAK = re.compile(
    r"(?<=[^\d\s][.!?])(?<!\be\.g\.)(?<!\bi\.e\.)\s*(?=[A-Z\d\"“(])"
    r"|\s{2,}(?=\d+\.\s)"
)


def number_lines(agreement: str) -> list[str]:
    """Clauses of the agreement; line N is lines[N - 1].

    Normally one clause per non-empty line. Text pasted without line breaks
    would otherwise become a single giant "line" that the model cannot cite
    precisely, so lines longer than LONG_LINE are split into sentences.
    """
    lines = []
    for line in agreement.splitlines():
        line = line.strip()
        if len(line) > LONG_LINE:
            lines.extend(part.strip() for part in _SENTENCE_BREAK.split(line) if part.strip())
        elif line:
            lines.append(line)
    return lines


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
    reason = None
    if verdict in REQUIRED_LINES:
        cited = covering if verdict == "included" else excluding
        if not (message_ok and any(c["valid"] for c in cited)):
            reason = "missing_evidence"
    # The prompt defines `included` as "a covering line applies and no
    # excluding line does". A model that cites a valid excluding line and
    # still says `included` contradicts its own evidence — and that mistake
    # means working for free, so it is never let through.
    if verdict == "included" and any(c["valid"] for c in excluding):
        reason = "conflicting_evidence"
    downgraded = reason is not None

    return {
        **item,
        "model_verdict": verdict,
        "verdict": "ambiguous" if downgraded else verdict,
        "evidence": {
            "message_quote_found": message_ok,
            "covering_lines": covering,
            "excluding_lines": excluding,
            "downgraded": downgraded,
            "downgrade_reason": reason,
        },
    }
