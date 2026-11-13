"""Safe project-file write helpers with atomic replacement and backups."""

import os
from pathlib import Path

def _resolve_target(workspace, relative_path):
    root = Path(workspace).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("Choose an existing workspace directory first.")
    raw = Path(relative_path)
    if raw.is_absolute():
        raise ValueError("Use a relative path inside the workspace.")
    target = (root / raw).resolve()
    if not target.is_relative_to(root):
        raise ValueError("Requested path escapes the selected workspace.")
    return root, target


def atomic_workspace_write(workspace, relative_path, content, backup=True):
    if not isinstance(content, str):
        raise ValueError("File content must be text.")
    root, target = _resolve_target(workspace, relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.is_dir():
        raise IsADirectoryError(str(target))
    temporary = target.with_name(target.name + ".pocket-tmp")
    backup_path = target.with_name(target.name + ".bak")
    try:
        temporary.write_text(content, encoding="utf-8", newline="")
        if backup and target.is_file():
            backup_path.write_bytes(target.read_bytes())
        os.replace(temporary, target)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return target.relative_to(root), backup_path if backup and backup_path.exists() else None
