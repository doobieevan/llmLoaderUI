import tempfile
import unittest
from pathlib import Path

from attachment_utils import build_attachment_context, load_text_attachment


class AttachmentTests(unittest.TestCase):
    def test_load_utf8_and_utf8_bom_text(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "notes.md"
            path.write_bytes(b"\xef\xbb\xbfhello")
            name, text, size = load_text_attachment(path)
            self.assertEqual((name, text), ("notes.md", "hello"))
            self.assertEqual(size, 8)

    def test_per_file_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "large.txt"
            path.write_bytes(b"12345")
            with self.assertRaisesRegex(ValueError, "limit"):
                load_text_attachment(path, max_bytes=4)

    def test_binary_and_invalid_utf8_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "picture.png"
            binary.write_bytes(b"\x89PNG\x00data")
            with self.assertRaisesRegex(ValueError, "Binary"):
                load_text_attachment(binary)
            invalid = Path(temp) / "bad.txt"
            invalid.write_bytes(b"\xff\xfe\xfa")
            with self.assertRaisesRegex(ValueError, "UTF-8"):
                load_text_attachment(invalid)

    def test_total_prompt_context_budget_is_bounded(self):
        context, omitted = build_attachment_context([("one.txt", "a" * 300), ("two.txt", "b" * 300)], max_chars=180)
        self.assertLessEqual(len(context), 180)
        self.assertGreaterEqual(omitted, 1)
        self.assertIn("one.txt", context)

    def test_zero_budget_produces_empty_context(self):
        context, omitted = build_attachment_context([("a.txt", "data")], max_chars=0)
        self.assertEqual(context, "")
        self.assertEqual(omitted, 1)


if __name__ == "__main__":
    unittest.main()
