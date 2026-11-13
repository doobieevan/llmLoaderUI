"""Opt-in privacy-conscious local event log with bounded size."""

import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

from app_paths import data_directory

MAX_LOG_BYTES = 2_000_000
_SECRET_PATTERN = re.compile(r"(?i)(password|token|authorization|api[_-]?key)(\s*[:=]\s*)([^\s,;]+)")


def default_log_path():
    return data_directory() / "activity.jsonl"


def default_failure_log_path():
    return data_directory() / "failures.jsonl"


def redact(text):
    return _SECRET_PATTERN.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", str(text))


class ActivityLogger:
    def __init__(self, path=None, enabled=False, max_bytes=MAX_LOG_BYTES):
        self.path = Path(path or default_log_path())
        self.enabled = bool(enabled)
        self.max_bytes = max(4096, int(max_bytes))
        self._lock = threading.Lock()

    def log(self, event, **fields):
        if not self.enabled:
            return False
        record = {"time": datetime.now(timezone.utc).isoformat(), "event": redact(event)}
        record.update({key: redact(value) for key, value in fields.items()})
        data = (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        try:
            with self._lock:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                if self.path.exists() and self.path.stat().st_size + len(data) > self.max_bytes:
                    old = self.path.read_bytes()
                    trimmed = old[-(self.max_bytes // 2):]
                    newline = trimmed.find(b"\n")
                    if newline >= 0:
                        trimmed = trimmed[newline + 1:]
                    self.path.write_bytes(trimmed)
                with self.path.open("ab") as stream:
                    stream.write(data)
            return True
        except OSError:
            return False

    def failure(self, component, error):
        """Record failure type only; exception text can contain paths or user data."""
        return self.log("failure", component=str(component)[:80], error_type=type(error).__name__)

    def clear(self):
        try:
            with self._lock:
                self.path.unlink(missing_ok=True)
            return True
        except OSError:
            return False
