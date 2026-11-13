"""GGUF directory discovery and persistent model-library configuration."""

import json
import os
from pathlib import Path

from app_paths import config_directory, default_models_directory

DEFAULT_MODELS_DIR = default_models_directory()
MAX_DISCOVERED_MODELS = 5000


def is_projector_model(path):
    """Projector/mmproj GGUFs are auxiliary vision weights, not chat models."""
    return Path(path).stem.casefold().startswith("mmproj")


def config_path():
    return config_directory() / "model_library.json"


def _dedupe_key(path):
    return os.path.normcase(str(path))


def load_directories(config=None):
    config = Path(config or config_path())
    folders = [DEFAULT_MODELS_DIR]
    known = {_dedupe_key(DEFAULT_MODELS_DIR)}
    try:
        data = json.loads(config.read_text(encoding="utf-8"))
        directories = data.get("directories", [])
        if not isinstance(directories, list):
            return folders
        for item in directories:
            if not isinstance(item, str) or not item.strip():
                continue
            candidate = Path(item).expanduser()
            try:
                normalized = candidate.resolve(strict=False)
            except (OSError, RuntimeError, ValueError):
                normalized = candidate.absolute()
            key = _dedupe_key(normalized)
            if key not in known:
                folders.append(normalized)
                known.add(key)
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return folders


def save_directories(directories, config=None):
    config = Path(config or config_path())
    config.parent.mkdir(parents=True, exist_ok=True)
    unique = []
    known = {_dedupe_key(DEFAULT_MODELS_DIR)}
    for directory in directories:
        try:
            path = Path(directory).expanduser().resolve(strict=False)
        except (OSError, RuntimeError, ValueError):
            continue
        key = _dedupe_key(path)
        if key not in known and path.is_absolute():
            unique.append(path)
            known.add(key)
    temporary = config.with_suffix(config.suffix + ".tmp")
    temporary.write_text(json.dumps({"directories": [str(p) for p in unique]}, indent=2), encoding="utf-8")
    temporary.replace(config)


def model_label(path):
    path = Path(path)
    return f"{path.name} — {path.parent}"


def discover_models(directories, limit=MAX_DISCOVERED_MODELS):
    if limit <= 0:
        return []
    found = {}
    for directory in directories:
        root = Path(directory).expanduser()
        if not root.is_dir():
            continue

        def walk_error(_error):
            return None

        try:
            for current, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
                dirs[:] = [name for name in dirs if not (Path(current) / name).is_symlink()]
                for name in files:
                    path = Path(current) / name
                    if path.suffix.casefold() != ".gguf" or is_projector_model(path):
                        continue
                    try:
                        if path.is_file():
                            resolved = path.resolve()
                            found[_dedupe_key(resolved)] = resolved
                    except (OSError, RuntimeError, ValueError):
                        continue
                    if len(found) >= limit:
                        return sorted(found.values(), key=lambda p: str(p).casefold())
        except (OSError, PermissionError, ValueError, RuntimeError):
            continue
    return sorted(found.values(), key=lambda p: str(p).casefold())
