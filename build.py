"""Portable PyInstaller build entrypoint: python build.py [--onefile]."""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--onefile", action="store_true", help="Bundle as one executable rather than a directory")
    parser.add_argument("--name", default="PocketGGUFCoder")
    args = parser.parse_args()
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--name", args.name]
    command += ["--onefile"] if args.onefile else ["--onedir"]
    command += ["--collect-all", "llama_cpp", "main.py"]
    return subprocess.run(command, cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
