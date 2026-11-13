"""Optional authenticated browser chat UI for the desktop GGUF app."""

import hmac
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

MAX_BODY_BYTES = 64_000

HTML = r'''<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pocket GGUF Coder</title>
<style>body{font:16px system-ui;max-width:900px;margin:2rem auto;padding:0 1rem;background:#111827;color:#e5e7eb}textarea,input,button{font:inherit;padding:.7rem;border-radius:.5rem}textarea{width:100%;height:9rem;box-sizing:border-box;background:#1f2937;color:white}input{width:100%;box-sizing:border-box;margin:.5rem 0;background:#1f2937;color:white}button{cursor:pointer;margin:.5rem 0}pre{white-space:pre-wrap;background:#1f2937;padding:1rem;border-radius:.5rem;min-height:8rem}.small{color:#9ca3af;font-size:.9rem}</style></head>
<body><h1>Pocket GGUF Coder</h1><p class="small">Requests go to your desktop host and local model. Browser mode does not execute tools or edit files.</p>
<label>Access password</label><input id="pw" type="password" autocomplete="current-password" placeholder="Paste password shown by desktop app">
<label>Prompt</label><textarea id="prompt" placeholder="Ask your local model..."></textarea><button id="send">Send</button><pre id="out"></pre>
<script>document.getElementById('send').onclick=async()=>{let o=document.getElementById('out');o.textContent='Generating...';try{let r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+document.getElementById('pw').value},body:JSON.stringify({prompt:document.getElementById('prompt').value})});let d=await r.json();o.textContent=r.ok?d.reply:(d.error||r.statusText)}catch(e){o.textContent='Request failed: '+e}}</script></body></html>'''


def lan_bind_confirmation(host):
    return host in ("0.0.0.0", "::")


class BrowserChatServer:
    def __init__(self, model_provider, host="127.0.0.1", port=8765, allow_lan=False, password=None, max_tokens=512, inference_lock=None):
        if lan_bind_confirmation(host) and not allow_lan:
            raise ValueError("Binding to the LAN requires explicit allow_lan=True.")
        if not password or len(password) < 16:
            raise ValueError("A server password of at least 16 characters is required.")
        self.model_provider = model_provider
        self.host = host
        self.port = int(port)
        self.password = password
        self.max_tokens = max(16, min(int(max_tokens), 2048))
        self.inference_lock = inference_lock or threading.Lock()
        self.httpd = None
        self.thread = None

    def start(self):
        if self.httpd:
            return self.httpd.server_address
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, _format, *_args):
                return

            def _json(self, code, payload):
                raw = json.dumps(payload).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                if urlparse(self.path).path != "/":
                    self._json(404, {"error": "Not found"})
                    return
                raw = HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):
                if urlparse(self.path).path != "/api/chat":
                    self._json(404, {"error": "Not found"})
                    return
                auth = self.headers.get("Authorization", "")
                supplied = auth[7:] if auth.startswith("Bearer ") else ""
                if not hmac.compare_digest(supplied.encode("utf-8"), owner.password.encode("utf-8")):
                    self._json(401, {"error": "Unauthorized"})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length <= 0 or length > MAX_BODY_BYTES:
                        raise ValueError("Request body must be between 1 byte and 64 KB.")
                    body = json.loads(self.rfile.read(length).decode("utf-8"))
                    prompt = body.get("prompt") if isinstance(body, dict) else None
                    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 12000:
                        raise ValueError("Prompt must be non-empty and at most 12,000 characters.")
                    if body.get("tools"):
                        raise ValueError("Browser clients cannot request tool execution.")
                    model = owner.model_provider()
                    if model is None:
                        self._json(409, {"error": "No local model is loaded in the desktop app."})
                        return
                    with owner.inference_lock:
                        result = model.create_chat_completion(
                            messages=[
                                {"role": "system", "content": "You are a local assistant accessed through an authenticated browser. Answer questions and provide code, but do not claim to run tools, inspect files, or modify the host."},
                                {"role": "user", "content": prompt},
                            ], max_tokens=owner.max_tokens, temperature=0.3, stream=False,
                        )
                    reply = result["choices"][0]["message"]["content"]
                    self._json(200, {"reply": reply})
                except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                    self._json(400, {"error": str(exc)})
                except Exception:
                    self._json(500, {"error": "Local inference request failed."})

        self.httpd = ThreadingHTTPServer((self.host, self.port), Handler)
        self.httpd.daemon_threads = True
        self.thread = threading.Thread(target=self.httpd.serve_forever, name="pocket-browser-server", daemon=True)
        self.thread.start()
        self.port = self.httpd.server_address[1]
        return self.httpd.server_address

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
            self.thread = None
