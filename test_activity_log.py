import json
import tempfile
import unittest
from pathlib import Path

from activity_log import ActivityLogger, redact


class ActivityLogTests(unittest.TestCase):
    def test_disabled_logger_writes_nothing(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "events.jsonl"
            logger = ActivityLogger(path, enabled=False)
            self.assertFalse(logger.log("tool_action", tool="write_file"))
            self.assertFalse(path.exists())

    def test_enabled_log_contains_event_but_not_prompt_content(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "events.jsonl"
            logger = ActivityLogger(path, enabled=True)
            logger.log("prompt_received", attachment_count=2)
            event = json.loads(path.read_text(encoding="utf-8").strip())
            self.assertEqual(event["event"], "prompt_received")
            self.assertEqual(event["attachment_count"], "2")
            self.assertNotIn("prompt", event)

    def test_secret_fields_redacted_and_log_bounded(self):
        self.assertNotIn("abc123", redact("password=abc123"))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "events.jsonl"
            logger = ActivityLogger(path, enabled=True, max_bytes=4096)
            for index in range(100):
                logger.log("tool", index=index, outcome="x" * 100)
            self.assertLessEqual(path.stat().st_size, 4096)

    def test_failure_log_records_type_not_exception_text(self):
        class SensitiveFailure(Exception):
            pass
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "failures.jsonl"
            logger = ActivityLogger(path, enabled=True)
            logger.failure("model_load", SensitiveFailure("private prompt phrase C:/Users/secret"))
            content = path.read_text(encoding="utf-8")
            event = json.loads(content.strip())
            self.assertEqual(event["event"], "failure")
            self.assertEqual(event["component"], "model_load")
            self.assertEqual(event["error_type"], "SensitiveFailure")
            self.assertNotIn("private prompt phrase", content)
            self.assertNotIn("C:/Users/secret", content)

    def test_clear_log(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "events.jsonl"
            logger = ActivityLogger(path, enabled=True)
            logger.log("started")
            self.assertTrue(logger.clear())
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
