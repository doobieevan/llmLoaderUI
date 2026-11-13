import unittest

from tool_registry import ToolSpec, ToolRegistry, default_registry


class ToolRegistryTests(unittest.TestCase):
    def test_default_tools_exposed(self):
        names = {tool["tool"] for tool in default_registry().describe()}
        self.assertEqual(names, {"read_file", "list_files", "docker_ps", "write_file", "run_command"})

    def test_workspace_write_auto_and_read_only_policy(self):
        registry = default_registry()
        action = {"tool": "write_file", "path": "src/a.py", "content": "pass"}
        self.assertEqual(registry.authorize("write_file", action, "Auto (Workspace)"), "allow")
        self.assertEqual(registry.authorize("write_file", action, "Read-Only", auto_approve_workspace=True), "deny")
        self.assertEqual(registry.authorize("write_file", action, "Ask Before Acting"), "confirm")
        self.assertEqual(registry.authorize("write_file", action, "Ask Before Acting", auto_approve_workspace=True), "allow")

    def test_opt_in_auto_approve_never_elevates_read_only(self):
        registry = default_registry()
        edit = {"tool": "write_file", "path": "src/a.py", "content": "pass"}
        safe = {"tool": "run_command", "command": "git diff --check"}
        unsafe = {"tool": "run_command", "command": "powershell Remove-Item *"}
        self.assertEqual(registry.authorize("write_file", edit, "Read-Only"), "deny")
        self.assertEqual(registry.authorize("write_file", edit, "Ask Before Acting"), "confirm")
        self.assertEqual(registry.authorize("write_file", edit, "Auto (Workspace)"), "allow")
        self.assertEqual(registry.authorize("run_command", safe, "Auto (Workspace)", True), "allow")
        self.assertEqual(registry.authorize("run_command", unsafe, "Auto (Workspace)", False), "deny")

    def test_only_allowlisted_commands_auto_run(self):
        registry = default_registry()
        safe = {"tool": "run_command", "command": "git diff --check"}
        unsafe = {"tool": "run_command", "command": "powershell Remove-Item *"}
        self.assertEqual(registry.authorize("run_command", safe, "Auto (Workspace)", True), "allow")
        self.assertEqual(registry.authorize("run_command", unsafe, "Auto (Workspace)", False), "deny")
        self.assertEqual(registry.authorize("run_command", safe, "Ask Before Acting", True, auto_approve_workspace=True), "allow")
        self.assertEqual(registry.authorize("run_command", unsafe, "Ask Before Acting", False, auto_approve_workspace=True), "deny")
        self.assertEqual(registry.authorize("run_command", unsafe, "Ask Before Acting"), "confirm")

    def test_unknown_or_incomplete_tool_is_denied(self):
        registry = default_registry()
        self.assertEqual(registry.authorize("missing", {"tool": "missing"}, "Auto (Workspace)"), "deny")
        self.assertEqual(registry.authorize("write_file", {"tool": "write_file", "path": "x"}, "Auto (Workspace)"), "deny")
        self.assertEqual(registry.authorize("write_file", {"tool": "write_file", "path": "x", "content": 12}, "Auto (Workspace)"), "deny")
        self.assertEqual(registry.authorize("write_file", {"tool": "write_file", "path": "x", "content": "a", "extra": "b"}, "Auto (Workspace)"), "deny")

    def test_extensions_must_register_callable_once(self):
        registry = ToolRegistry()
        registry.register(ToolSpec("hello", "test", "read", ("value",)), lambda action: action["value"])
        self.assertEqual(registry.execute("hello", {"tool": "hello", "value": "ok"}, "Read-Only"), "ok")
        with self.assertRaises(ValueError):
            registry.register(ToolSpec("hello", "duplicate", "read", ()), lambda action: None)


if __name__ == "__main__":
    unittest.main()
