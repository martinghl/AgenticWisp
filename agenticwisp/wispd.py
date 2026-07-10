"""AgenticWisp 状态中枢:按 session_id 存细状态,喂给所有显示端。"""
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from agenticwisp import protocol
from agenticwisp.page import render_page
from agenticwisp import roster

DEFAULT_PORT = 9099


class SessionStore:
    """线程安全:按 session_id 存 {state, tool, updated_at}。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._sessions = {}

    def update(self, session_id, state, tool=None, now=None):
        norm = protocol.normalize(state)
        if norm is None:
            return None
        sid = session_id or "legacy"
        with self._lock:
            self._sessions[sid] = {
                "state": norm,
                "tool": tool,
                "updated_at": now if now is not None else time.time(),
            }
        return norm

    def snapshot(self):
        with self._lock:
            return {sid: dict(v) for sid, v in self._sessions.items()}


def build_sessions(roster_map, store_snapshot):
    """合并花名册与细状态 → [{id,name,cwd,state,tool}]。花名册优先给名字/cwd。
    花名册非空时,不在花名册的 store-only session 视为已结束、丢弃(避免死 session
    永久 pin 聚合灯);花名册为空(不可用)时保留所有 store session 作为 fallback。"""
    out = []
    for sid, meta in roster_map.items():
        detail = store_snapshot.get(sid)
        if detail:
            state, tool = detail["state"], detail.get("tool")
        else:
            state = protocol.THINKING if meta.get("status") == "busy" else protocol.IDLE
            tool = None
        out.append({"id": sid, "name": meta.get("name", sid[:8]),
                    "cwd": meta.get("cwd", ""), "state": state, "tool": tool})
    if not roster_map:
        for sid, detail in store_snapshot.items():
            out.append({"id": sid, "name": sid[:8], "cwd": "",
                        "state": detail["state"], "tool": detail.get("tool")})
    return out


def make_handler(store, sessions_dir="~/.claude/sessions"):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, code, body, ctype="text/plain; charset=utf-8"):
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _sessions(self):
            return build_sessions(roster.read_roster(sessions_dir), store.snapshot())

        def do_GET(self):
            if self.path == "/state":
                self._send(200, protocol.aggregate(s["state"] for s in self._sessions()))
            elif self.path == "/aggregate":
                self._send(200, protocol.aggregate(s["state"] for s in self._sessions()))
            elif self.path == "/sessions":
                self._send(200, json.dumps(self._sessions(), ensure_ascii=False),
                           "application/json; charset=utf-8")
            elif self.path == "/":
                self._send(200, render_page(), "text/html; charset=utf-8")
            else:
                self._send(404, "not found")

        def do_POST(self):
            if self.path != "/state":
                self._send(404, "not found")
                return
            length = int(self.headers.get("Content-Length", 0) or 0)
            raw = self.rfile.read(length).decode("utf-8") if length else ""
            try:
                payload = json.loads(raw) if raw.strip().startswith("{") else {"state": raw.strip()}
            except ValueError:
                payload = {"state": raw.strip()}
            result = store.update(payload.get("session_id"),
                                  payload.get("state"),
                                  payload.get("tool"))
            if result is None:
                self._send(400, "invalid state")
            else:
                self._send(200, result)

    return Handler


def serve(port=DEFAULT_PORT, store=None, sessions_dir="~/.claude/sessions"):
    store = store if store is not None else SessionStore()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(store, sessions_dir))
    return httpd, store


def main():
    port = int(os.environ.get("WISP_PORT", DEFAULT_PORT))
    httpd, _ = serve(port)
    print(f"AgenticWisp 状态中枢监听 127.0.0.1:{port}(Ctrl-C 退出)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    main()
