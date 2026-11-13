import unittest

from assistant_utils import extract_tool_actions
from tool_registry import default_registry


class ToolActionParsingTests(unittest.TestCase):
    def test_tool_fence(self):
        text = 'Plan first.\n```tool\n{"tool":"write_file","path":"a.py","content":"pass"}\n```'
        self.assertEqual(extract_tool_actions(text), [{"tool": "write_file", "path": "a.py", "content": "pass"}])

    def test_json_fence(self):
        text = '```json\n{"tool":"read_file","path":"src/a.py"}\n```'
        self.assertEqual(extract_tool_actions(text), [{"tool": "read_file", "path": "src/a.py"}])

    def test_standalone_json_object_line(self):
        text = 'Creating the file now.\n{"tool":"write_file","path":"src/a.py","content":"pass"}\nDone.'
        self.assertEqual(extract_tool_actions(text)[0]["tool"], "write_file")

    def test_pretty_printed_standalone_object(self):
        text = 'Action:\n{\n  "tool": "write_file",\n  "path": "src/a.py",\n  "content": "pass"\n}\nDone.'
        parsed = extract_tool_actions(text)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["path"], "src/a.py")

    def test_deduplicate_same_action(self):
        action = '{"tool":"list_files"}'
        text = f'```json\n{action}\n```\n{action}'
        self.assertEqual(extract_tool_actions(text), [{"tool": "list_files"}])

    def test_ignore_broken_json_schemas_and_examples_in_other_fences(self):
        text = (
            '```tool\n{broken}\n```\n'
            '```python\n{"tool":"write_file","path":"bad.py","content":"bad"}\n```\n'
            '```json\n{"path":"missing-tool"}\n```\n'
            '```json\n[1,2,3]\n```'
        )
        self.assertEqual(extract_tool_actions(text), [])

    def test_registry_rejects_unknown_fields_and_unregistered_tool(self):
        registry = default_registry()
        extra = {"tool": "write_file", "path": "a.py", "content": "pass", "admin": True}
        unknown = {"tool": "run_anything", "command": "whoami"}
        self.assertEqual(registry.authorize("write_file", extra, "Auto (Workspace)"), "deny")
        self.assertEqual(registry.authorize("run_anything", unknown, "Auto (Workspace)"), "deny")


if __name__ == "__main__":
    unittest.main()
