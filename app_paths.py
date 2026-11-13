"""Portable per-user data/config locations for Pocket GGUF Coder."""

import os
import sys
from pathlib import Path

APP_NAME = "PocketGGUFCoder"


def data_directory():
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return root / APP_NAME


def config_directory():
    if os.name == "nt":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Preferences"
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / APP_NAME


def default_models_directory():
    if getattr(sys, "frozen", False):
        return data_directory() / "models"
    return Path(__file__).resolve().parent / "models"
