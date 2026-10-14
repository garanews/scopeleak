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


def item(verdict, lines, quote="Could we take payments with Stripe?", other=()):
    """`lines` go in the list the verdict needs; `other` in the opposite list."""
    covering, excluding = (lines, list(other)) if verdict == "included" else (list(other), lines)
    return {"summary": "s", "message_quote": quote, "covering_lines": covering,
            "excluding_lines": excluding, "reasoning": "r", "verdict": verdict}


class LineReferences(unittest.TestCase):
    def test_numbering_skips_blank_lines(self):
        self.assertEqual(LINES[3], "Not included: e-commerce or online payments.")

    def test_text_without_line_breaks_is_split_into_clauses(self):
        flat = ("WEB DESIGN AGREEMENTDesigner (Us): Alex Chen. 1. Design and DevelopmentWe will build it."
                "Browser testing: We will not test in Internet Explorer [cite: 1.2.4].Mobile testing: "
                "current iOS devices, e.g. iPhones.   2. Text and PhotographsWe are not responsible for "
                "writing any text copy.You will provide all text.3. Changes and RevisionsNew pages are "
                "billed at our standard hourly rate of £60 per hour.")
        lines = evidence.number_lines(flat)
        self.assertGreater(len(lines), 5)
        self.assertIn("Browser testing: We will not test in Internet Explorer [cite: 1.2.4].", lines)
        self.assertTrue(any("e.g. iPhones" in line for line in lines))
        self.assertTrue(any(line.startswith("3. Changes") for line in lines))

    def test_short_lines_are_never_split(self):
        line = "On-Premise: no Docker (e.g., k3s). No hypervisors. Billed at EUR 80 per hour."
        self.assertEqual(evidence.number_lines(line), [line])

    def test_accepts_existing_lines_in_any_reasonable_form(self):
        for ref in ("L4", "l4", " L4 ", "4", 4):
            result = evidence.validate(item("extra", [ref]), LINES, MESSAGE)
            self.assertEqual(result["verdict"], "extra", ref)
            self.assertEqual(result["evidence"]["excluding_lines"][0]["text"], LINES[3])

    def test_rejects_lines_that_do_not_exist(self):
        for ref in ("L0", "L99", "line four", "", -1):
            result = evidence.validate(item("extra", [ref]), LINES, MESSAGE)
            self.assertFalse(result["evidence"]["excluding_lines"][0]["valid"], ref)
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

    def test_extra_backed_only_by_covering_lines_is_downgraded(self):
        # "Not mentioned in the agreement" is not evidence of extra work.
        result = evidence.validate(item("extra", [], other=["L2"]), LINES, MESSAGE)
        self.assertEqual(result["verdict"], "ambiguous")
        self.assertTrue(result["evidence"]["downgraded"])

    def test_included_backed_only_by_excluding_lines_is_downgraded(self):
        result = evidence.validate(item("included", [], other=["L4"]), LINES, MESSAGE)
        self.assertEqual(result["verdict"], "ambiguous")

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
