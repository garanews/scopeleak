"""Deterministic citation checks.

The model may reason however it likes, but every quote it hands back must
exist in the source documents. This module cannot tell whether a quote
*supports* a verdict — only whether it is real. That is the point: it is the
one part of the pipeline that is not probabilistic.
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


def validate(item: dict, agreement: str, message: str) -> dict:
    """Annotate one classified request with citation checks.

    A verdict of `included` or `extra` needs a real quote from the message and
    at least one real quote from the agreement; otherwise it is downgraded to
    `ambiguous`. The model's original verdict is kept for evaluation.
    """
    agreement_checks = [
        {"quote": q, "found": find_quote(q, agreement)}
        for q in item.get("agreement_quotes", [])
    ]
    message_ok = find_quote(item.get("message_quote", ""), message)
    agreement_ok = any(c["found"] for c in agreement_checks)

    verdict = item.get("verdict", "ambiguous")
    downgraded = verdict in ("included", "extra") and not (message_ok and agreement_ok)

    return {
        **item,
        "model_verdict": verdict,
        "verdict": "ambiguous" if downgraded else verdict,
        "evidence": {
            "message_quote_found": message_ok,
            "agreement_quotes": agreement_checks,
            "downgraded": downgraded,
        },
    }
