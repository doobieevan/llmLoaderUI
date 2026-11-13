import unittest

from assistant_utils import add_untrusted_context, build_chat_messages, extract_stream_text, is_tool_catalog, messages_to_prompt, strip_tool_output


class ChatTemplateTests(unittest.TestCase):
    def test_build_messages_has_system_history_current_and_attachments(self):
        messages = build_chat_messages(
            [{"role": "user", "content": "Earlier question"}, {"role": "assistant", "content": "Earlier answer"}],
            "Current request", "C:/work", "file.py: print(1)", '[{"tool":"read_file"}]', True,
        )
        self.assertEqual([m["role"] for m in messages], ["system", "user", "assistant", "user"])
        self.assertIn("Auto-approval is enabled", messages[0]["content"])
        self.assertIn("C:/work", messages[0]["content"])
        self.assertIn("answer the user's question directly", messages[0]["content"].casefold())
        self.assertIn("never output a catalog or schema as an action", messages[0]["content"].casefold())
        self.assertNotIn("required_fields", messages[0]["content"])
        self.assertNotIn("read_file(path)", messages[0]["content"])
        self.assertIn("Current request", messages[-1]["content"])
        self.assertIn("file.py", messages[-1]["content"])

    def test_prompt_fallback_retains_roles_and_system(self):
        prompt = messages_to_prompt([
            {"role": "system", "content": "system note"},
            {"role": "user", "content": "question"},
            {"role": "assistant", "content": "answer"},
        ])
        self.assertIn("System:\nsystem note", prompt)
        self.assertIn("User:\nquestion", prompt)
        self.assertTrue(prompt.endswith("Assistant:"))

    def test_add_context_labels_content_untrusted(self):
        original = [{"role": "system", "content": "base"}, {"role": "user", "content": "hello"}]
        updated = add_untrusted_context(original, "workspace", "README content")
        self.assertEqual(len(original), 2)
        self.assertIn("untrusted local context", updated[1]["content"].casefold())
        self.assertIn("README content", updated[1]["content"])

    def test_catalog_detection_and_visible_tool_stripping(self):
        catalog = '{"tool":"list_files","description":"List names","required_fields":[]}'
        self.assertTrue(is_tool_catalog(catalog))
        self.assertFalse(is_tool_catalog('{"tool":"write_file","path":"a.py","content":"pass"}'))
        answer = 'I wrote it.\n```tool\n{"tool":"write_file","path":"a.py","content":"pass"}\n```'
        self.assertEqual(strip_tool_output(answer), "I wrote it.")

    def test_chat_completion_chunk_shapes(self):
        self.assertEqual(extract_stream_text({"choices": [{"delta": {"content": "a"}}]}), "a")
        self.assertEqual(extract_stream_text({"choices": [{"message": {"content": "b"}}]}), "b")


if __name__ == "__main__":
    unittest.main()
