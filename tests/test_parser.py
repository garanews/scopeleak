import unittest

import fitz

from core import parser


class ExtractText(unittest.TestCase):
    def test_pdf(self):
        doc = fitz.open()
        doc.new_page().insert_text((72, 72), "Not included: online payments.")
        text = parser.extract_text("contract.PDF", doc.tobytes())
        self.assertIn("Not included: online payments.", text)

    def test_txt(self):
        self.assertEqual(parser.extract_text("a.txt", "Fee: EUR 2,400".encode()), "Fee: EUR 2,400")


if __name__ == "__main__":
    unittest.main()
