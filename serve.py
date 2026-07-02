#!/usr/bin/env python3
"""Threaded static server for the we_d900 breakdown page, plus a save endpoint.

GET / HEAD : serve files (with HTTP range support, needed for video seeking).
POST /api/save-prompt : {"task": "<slug>", "prompt": "<text>"}
    -> stores the prompt in a SEPARATE file (prompts.json) at the dataset root,
       keyed by task slug. tasks.parquet is never modified.

Run:  python3 serve.py [port]   (default 8000)
"""
import contextlib
import json
import os
import re
import socket
import sys
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT = os.path.join(os.path.dirname(ROOT), "we_d900")  # videos live here
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
PROMPTS_PATH = os.path.join(ROOT, "prompts_merged.json")
SLUG_RE = re.compile(r"^[A-Za-z0-9._-]+$")  # task dir names only; blocks path traversal
_lock = threading.Lock()  # serialize read-modify-write of prompts.json


def save_prompt(task: str, prompt: str) -> str:
    """Store `prompt` for `task` in prompts.json. Returns the file's relative path."""
    if not SLUG_RE.match(task):
        raise ValueError(f"invalid task name: {task!r}")
    if not os.path.isdir(os.path.join(ROOT, "assets", task)):
        raise FileNotFoundError(f"no such task directory: {task!r}")

    with _lock:
        data = {}
        if os.path.isfile(PROMPTS_PATH):
            try:
                with open(PROMPTS_PATH) as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    data = {}
            except (json.JSONDecodeError, OSError):
                data = {}
        entry = data.get(task, {})
        if isinstance(entry, dict):
            entry["prompt"] = prompt
        else:
            entry = prompt
        data[task] = entry
        tmp = PROMPTS_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp, PROMPTS_PATH)  # atomic
    return os.path.relpath(PROMPTS_PATH, ROOT)


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        result = super().translate_path(path)
        if not os.path.exists(result):
            rel = os.path.relpath(result, ROOT)
            fallback = os.path.join(DATA_ROOT, rel)
            if os.path.exists(fallback):
                return fallback
        return result

    def _json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path.split("?")[0] != "/api/save-prompt":
            self._json(404, {"ok": False, "error": "unknown endpoint"})
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(n) or b"{}")
            task = (data.get("task") or "").strip()
            prompt = data.get("prompt", "")
            if not isinstance(prompt, str):
                raise ValueError("prompt must be a string")
            prompt = prompt.strip()
            if not task:
                raise ValueError("missing task")
            if not prompt:
                raise ValueError("prompt is empty")
            rel = save_prompt(task, prompt)
            print(f"[save] {task!r} -> {rel}  ({prompt!r})")
            self._json(200, {"ok": True, "task": task, "path": rel, "prompt": prompt})
        except Exception as e:
            print(f"[save-error] {e}")
            self._json(400, {"ok": False, "error": str(e)})


class DualStackServer(ThreadingHTTPServer):
    address_family = socket.AF_INET6  # creates IPv6 socket; dual-stack accepts IPv4 too

    def server_bind(self):
        with contextlib.suppress(Exception):
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        return super().server_bind()

    def finish_request(self, request, client_address):
        # IPv4-mapped addresses arrive as bytes on dual-stack; decode them
        if isinstance(client_address[0], bytes):
            client_address = (client_address[0].decode("ascii"), *client_address[1:])
        super().finish_request(request, client_address)


if __name__ == "__main__":
    os.chdir(ROOT)
    server = DualStackServer(("", PORT), Handler)
    server.daemon_threads = True
    print(f"Serving {ROOT} on http://localhost:{PORT}/ (threaded, with /api/save-prompt)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()
