import tempfile
import unittest
from pathlib import Path

from safe_actions import approved_check_argv, resolve_workspace_target, run_approved_check, write_workspace_file
from project_files import atomic_workspace_write


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def test_atomic_write_preserves_backup(self):
        (self.root / "file.txt").write_text("old", encoding="utf-8")
        relative, backup = atomic_workspace_write(self.root, "file.txt", "new")
        self.assertEqual(relative, Path("file.txt"))
        self.assertEqual((self.root / "file.txt").read_text(encoding="utf-8"), "new")
        self.assertEqual(backup.read_text(encoding="utf-8"), "old")

    def test_workspace_file_write(self):
        relative = write_workspace_file(self.root, "src/demo.py", "print('ok')\n")
        self.assertEqual(relative, Path("src/demo.py"))
        self.assertEqual((self.root / relative).read_text(encoding="utf-8"), "print('ok')\n")

    def test_parent_traversal_rejected(self):
        with self.assertRaises(ValueError):
            resolve_workspace_target(self.root, "../outside.txt")

    def test_absolute_path_rejected(self):
        with self.assertRaises(ValueError):
            resolve_workspace_target(self.root, str(self.root / "outside.txt"))

    def test_symlink_escape_rejected(self):
        outside = Path(tempfile.gettempdir()).resolve() / "pocket-coder-outside-test.txt"
        try:
            (self.root / "escape.txt").symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation unavailable")
        with self.assertRaises(ValueError):
            resolve_workspace_target(self.root, "escape.txt")

    def test_write_size_limit(self):
        with self.assertRaises(ValueError):
            write_workspace_file(self.root, "large.txt", "x" * 1_000_001)

    def test_fixed_checks_allowlisted(self):
        self.assertEqual(approved_check_argv("git diff --check"), ["git", "diff", "--check"])
        argv = approved_check_argv("python -m compileall .")
        self.assertEqual(argv[0], __import__("sys").executable)
        self.assertEqual(argv[1:], ["-m", "compileall", "."])
        self.assertEqual(approved_check_argv("ruff check ."), ["ruff", "check", "."])

    def test_arbitrary_shell_and_chaining_rejected(self):
        for command in ("powershell Remove-Item *", "git diff --check; whoami", "python -c 'print(1)'", "git diff --check | more"):
            with self.subTest(command=command):
                self.assertIsNone(approved_check_argv(command))

    def test_runner_refuses_unlisted_command(self):
        with self.assertRaises(ValueError):
            run_approved_check("whoami", self.root)


if __name__ == "__main__":
    unittest.main()
