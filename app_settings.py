"""Atomic, portable user settings storage with defensive value normalization."""

import json
import os
from pathlib import Path

from app_paths import config_directory

PERMISSION_MODES = {"Read-Only", "Ask Before Acting", "Auto (Workspace)"}


def settings_path():
    return config_directory() / "settings.json"


def normalize_settings(value, cpu_count=None):
    value = value if isinstance(value, dict) else {}
    cpu_count = max(1, int(cpu_count or os.cpu_count() or 1))
    try:
        temperature = min(2.0, max(0.0, float(value.get("temperature", 0.3))))
    except (TypeError, ValueError):
        temperature = 0.3
    try:
        threads = min(cpu_count, max(1, int(value.get("cpu_threads", max(1, cpu_count - 1)))))
    except (TypeError, ValueError):
        threads = max(1, cpu_count - 1)
    mode = value.get("permission_mode", "Auto (Workspace)")
    if mode not in PERMISSION_MODES:
        mode = "Auto (Workspace)"
    return {
        "temperature": temperature,
        "cpu_threads": threads,
        "permission_mode": mode,
        "auto_approve_workspace": bool(value.get("auto_approve_workspace", False)),
        "include_context": bool(value.get("include_context", False)),
        "tts_executable": value.get("tts_executable", "") if isinstance(value.get("tts_executable", ""), str) else "",
        "tts_args": value.get("tts_args", "{text}") if isinstance(value.get("tts_args", "{text}"), str) else "{text}",
        "tts_enabled": bool(value.get("tts_enabled", False)),
        "last_model_path": value.get("last_model_path", "") if isinstance(value.get("last_model_path", ""), str) else "",
        "workspace": value.get("workspace", "") if isinstance(value.get("workspace", ""), str) else "",
        "context_tokens": max(512, min(32768, int(value.get("context_tokens", 4096)))) if str(value.get("context_tokens", 4096)).isdigit() else 4096,
        "browser_server_enabled": bool(value.get("browser_server_enabled", False)),
        "browser_server_allow_lan": bool(value.get("browser_server_allow_lan", False)),
        "browser_server_port": max(1024, min(65535, int(value.get("browser_server_port", 8765)))) if str(value.get("browser_server_port", 8765)).isdigit() else 8765,
        "activity_log_enabled": bool(value.get("activity_log_enabled", False)),
        "failure_log_enabled": bool(value.get("failure_log_enabled", False)),
        "attachment_file_limit_mb": max(1, min(64, int(value.get("attachment_file_limit_mb", 8)))) if str(value.get("attachment_file_limit_mb", 8)).isdigit() else 8,
        "attachment_context_chars": max(4000, min(200000, int(value.get("attachment_context_chars", 48000)))) if str(value.get("attachment_context_chars", 48000)).isdigit() else 48000,
    }


def load_settings(path=None):
    target = Path(path or settings_path())
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        value = {}
    return normalize_settings(value)


def save_settings(values, path=None):
    target = Path(path or settings_path())
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(normalize_settings(values), ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, target)
