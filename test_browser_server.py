import json
import threading
import unittest
import urllib.error
import urllib.request

from browser_server import BrowserChatServer, lan_bind_confirmation


class BrowserServerTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        class FakeModel:
            def create_chat_completion(inner, messages, **kwargs):
                self_outer.calls.append(messages)
                return {"choices": [{"message": {"content": "Local reply"}}]}
        self_outer = self
        self.model = FakeModel()
        self.password = "test-password-long-enough"
        self.server = BrowserChatServer(lambda: self.model, port=0, password=self.password)
        host, port = self.server.start()
        self.url = f"http://{host}:{port}"

    def tearDown(self):
        self.server.stop()

    def request(self, path, payload=None, token=None):
        data = None if payload is None else json.dumps(payload).encode()
        headers = {}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(self.url + path, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=3) as response:
                return response.status, response.read().decode()
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, exc.read().decode()
            finally:
                exc.close()

    def test_home_page_and_authenticated_chat(self):
        status, html = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn("Pocket GGUF Coder", html)
        status, _ = self.request("/api/chat", {"prompt": "hello"}, self.password)
        self.assertEqual(status, 200)
        self.assertEqual(self.calls[-1][-1]["content"], "hello")

    def test_unauthorized_and_tools_rejected(self):
        status, _ = self.request("/api/chat", {"prompt": "hello"}, "wrong")
        self.assertEqual(status, 401)
        before = len(self.calls)
        status, _ = self.request("/api/chat", {"prompt": "hello", "tools": [{"tool": "write_file"}]}, self.password)
        self.assertEqual(status, 400)
        self.assertEqual(len(self.calls), before)

    def test_bad_prompt_and_missing_model_rejected(self):
        status, _ = self.request("/api/chat", {"prompt": " "}, self.password)
        self.assertEqual(status, 400)
        server = BrowserChatServer(lambda: None, port=0, password=self.password)
        host, port = server.start()
        try:
            req = urllib.request.Request(f"http://{host}:{port}/api/chat", data=b'{"prompt":"hi"}', headers={"Authorization": "Bearer " + self.password, "Content-Type": "application/json"})
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(req, timeout=3)
            try:
                self.assertEqual(caught.exception.code, 409)
            finally:
                caught.exception.close()
        finally:
            server.stop()

    def test_trusted_lan_requires_explicit_opt_in(self):
        self.assertTrue(lan_bind_confirmation("0.0.0.0"))
        self.assertFalse(lan_bind_confirmation("127.0.0.1"))
        with self.assertRaises(ValueError):
            BrowserChatServer(lambda: self.model, host="0.0.0.0", port=0, password=self.password, allow_lan=False)

    def test_server_password_required(self):
        with self.assertRaises(ValueError):
            BrowserChatServer(lambda: self.model, password="short")


if __name__ == "__main__":
    unittest.main()
