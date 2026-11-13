"""Workspace-bounded automation policy for Pocket GGUF Coder."""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from project_files import atomic_workspace_write

MAX_AUTO_WRITE_BYTES = 1_000_000


def sys_executable():
    import sys
    return sys.executable


# Fixed commands avoid shell parsing and do not accept model-provided arguments.
SAFE_CHECKS = {
    "python -m compileall .": [sys_executable(), "-m", "compileall", "."],
    "git diff --check": ["git", "diff", "--check"],
    "ruff check .": ["ruff", "check", "."],
}


def resolve_workspace_target(workspace, relative_path):
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


def write_workspace_file(workspace, relative_path, content):
    if not isinstance(content, str):
        raise ValueError("File content must be text.")
    if len(content.encode("utf-8")) > MAX_AUTO_WRITE_BYTES:
        raise ValueError("Automatic writes are limited to 1 MB per file.")
    root, target = resolve_workspace_target(workspace, relative_path)
    relative = target.relative_to(root)
    written, _backup = atomic_workspace_write(root, relative, content)
    return written


def approved_check_argv(command):
    if not isinstance(command, str) or any(ch in command for ch in ";&|<>`$\n\r"):
        return None
    try:
        words = shlex.split(command, posix=True)
    except ValueError:
        return None
    normalized = " ".join(words)
    fixed_argv = SAFE_CHECKS.get(normalized)
    if fixed_argv:
        return list(fixed_argv)
    if normalized == "ruff check .":
        ruff = shutil.which("ruff")
        return [ruff, "check", "."] if ruff else None
    return None


def run_approved_check(command, workspace, timeout=120):
    argv = approved_check_argv(command)
    if argv is None:
        raise ValueError("Only the built-in fixed check commands are allowed in Auto (Workspace) mode.")
    root = Path(workspace).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("Choose an existing workspace directory first.")
    if os.name == "nt" and Path(argv[0]).name.casefold() == "git":
        git = shutil.which("git")
        if not git:
            raise FileNotFoundError("Git is not installed or not available on PATH.")
        argv[0] = git
    result = subprocess.run(argv, cwd=str(root), capture_output=True, text=True, timeout=timeout, shell=False)
    output = (result.stdout + ("\n" + result.stderr if result.stderr else "")).strip()
    return result.returncode, output
