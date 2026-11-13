import unittest

from agent_loop import limit_tool_actions, may_execute_tool_actions, run_agent_loop


class AgentLoopTests(unittest.TestCase):
    def test_tool_results_are_fed_back_and_model_finishes(self):
        responses = iter([
            '```tool\n{"tool":"read_file","path":"a.py"}\n```',
            'The file contains a function.',
        ])
        calls = []
        def generate(messages):
            calls.append(messages)
            return next(responses)
        final, transcript, steps = run_agent_loop(
            [{"role": "user", "content": "Inspect a.py"}], generate,
            lambda action: "source is safe",
        )
        self.assertEqual(steps, 1)
        self.assertEqual(final, "The file contains a function.")
        self.assertIn("source is safe", calls[1][-1]["content"])
        self.assertIn("untrusted", calls[1][-1]["content"])

    def test_denial_result_also_returns_to_model(self):
        responses = iter(['{"tool":"run_command","command":"format C:"}', 'Stopped safely.'])
        final, _transcript, steps = run_agent_loop(
            [], lambda _messages: next(responses),
            lambda _action: "Denied: unsafe command.",
        )
        self.assertEqual(steps, 1)
        self.assertEqual(final, "Stopped safely.")

    def test_round_limit_is_enforced(self):
        calls = []
        def generate(_messages):
            calls.append(1)
            return '{"tool":"list_files"}'
        responses = iter(['{"tool":"list_files"}', '{"tool":"list_files"}', '{"tool":"list_files"}', 'Stopped at the tool limit.'])
        calls = []
        def generate(messages):
            calls.append(messages)
            return next(responses)
        final, transcript, steps = run_agent_loop([], generate, lambda _action: "ok", max_steps=2)
        self.assertEqual(len(calls), 4)
        self.assertEqual(steps, 2)
        self.assertEqual(final, "Stopped at the tool limit.")
        self.assertIn("Tool-step limit reached", calls[3][-1]["content"])

    def test_action_limit_and_round_gate(self):
        actions = [{"tool": "read_file", "path": str(i)} for i in range(9)]
        self.assertEqual(len(limit_tool_actions(actions, 3)), 3)
        self.assertTrue(may_execute_tool_actions(0, 3))
        self.assertFalse(may_execute_tool_actions(3, 3))

    def test_stop_before_generation(self):
        generated = []
        final, transcript, steps = run_agent_loop([], lambda _messages: generated.append(1) or "unused", lambda _action: None, stop_requested=lambda: True)
        self.assertEqual(generated, [])
        self.assertEqual(final, "")
        self.assertEqual(steps, 0)


if __name__ == "__main__":
    unittest.main()
