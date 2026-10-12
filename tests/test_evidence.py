"""Reference integrity validation, tested on synthetic model output (no LLM)."""
import unittest

from core import evidence

AGREEMENT = """WEB DESIGN AGREEMENT

The website consists of five (5) pages.
The fee includes two (2) rounds of revisions.
Not included: e-commerce or online payments.
"""
MESSAGE = "Could we take payments with Stripe? Thanks!"
LINES = evidence.number_lines(AGREEMENT)


def item(verdict, lines, quote="Could we take payments with Stripe?"):
    return {"summary": "s", "message_quote": quote, "agreement_lines": lines,
            "reasoning": "r", "verdict": verdict}


class LineReferences(unittest.TestCase):
    def test_numbering_skips_blank_lines(self):
        self.assertEqual(LINES[3], "Not included: e-commerce or online payments.")

    def test_accepts_existing_lines_in_any_reasonable_form(self):
        for ref in ("L4", "l4", " L4 ", "4", 4):
            result = evidence.validate(item("extra", [ref]), LINES, MESSAGE)
            self.assertEqual(result["verdict"], "extra", ref)
            self.assertEqual(result["evidence"]["agreement_lines"][0]["text"], LINES[3])

    def test_rejects_lines_that_do_not_exist(self):
        for ref in ("L0", "L99", "line four", "", -1):
            result = evidence.validate(item("extra", [ref]), LINES, MESSAGE)
            self.assertFalse(result["evidence"]["agreement_lines"][0]["valid"], ref)
            self.assertEqual(result["verdict"], "ambiguous", ref)

    def test_one_valid_line_is_enough(self):
        result = evidence.validate(item("extra", ["L99", "L4"]), LINES, MESSAGE)
        self.assertEqual(result["verdict"], "extra")


class Downgrades(unittest.TestCase):
    def test_verdict_without_lines_is_downgraded_and_recorded(self):
        for verdict in ("included", "extra"):
            result = evidence.validate(item(verdict, []), LINES, MESSAGE)
            self.assertEqual(result["verdict"], "ambiguous")
            self.assertEqual(result["model_verdict"], verdict)
            self.assertTrue(result["evidence"]["downgraded"])

    def test_invented_message_quote_is_downgraded(self):
        result = evidence.validate(item("extra", ["L4"], quote="please add PayPal too"), LINES, MESSAGE)
        self.assertEqual(result["verdict"], "ambiguous")
        self.assertFalse(result["evidence"]["message_quote_found"])

    def test_ambiguous_needs_no_evidence(self):
        result = evidence.validate(item("ambiguous", []), LINES, MESSAGE)
        self.assertEqual(result["verdict"], "ambiguous")
        self.assertFalse(result["evidence"]["downgraded"])

    def test_quote_matching_ignores_case_whitespace_and_curly_quotes(self):
        self.assertTrue(evidence.find_quote("COULD  we take\npayments", MESSAGE))
        self.assertTrue(evidence.find_quote("it’s fine", "It's fine by us"))


if __name__ == "__main__":
    unittest.main()
