import http.client
import json
import tempfile
import threading
import unittest

from agenticwisp import protocol
from agenticwisp.wispd import SessionStore, serve, build_sessions


class BuildSessionsTest(unittest.TestCase):
    def test_joins_roster_and_details(self):
        roster_map = {"a": {"name": "Wisp", "cwd": "/home/user/project", "status": "busy"}}
        snap = {"a": {"state": "tool", "tool": "Bash", "updated_at": 0}}
        rows = build_sessions(roster_map, snap)
        self.assertEqual(rows, [{"id": "a", "name": "Wisp", "cwd": "/home/user/project",
                                 "state": "tool", "tool": "Bash"}])

    def test_roster_without_detail_uses_status(self):
        rows = build_sessions({"a": {"name": "X", "cwd": "/x", "status": "busy"}}, {})
        self.assertEqual(rows[0]["state"], protocol.THINKING)
        rows2 = build_sessions({"b": {"name": "Y", "cwd": "/y", "status": None}}, {})
        self.assertEqual(rows2[0]["state"], protocol.IDLE)

    def test_detail_without_roster_still_listed(self):
        rows = build_sessions({}, {"legacy": {"state": "error", "tool": None, "updated_at": 0}})
        self.assertEqual(rows[0]["id"], "legacy")
        self.assertEqual(rows[0]["state"], protocol.ERROR)

    def test_dead_store_session_dropped_when_roster_present(self):
        roster_map = {"live": {"name": "L", "cwd": "/l", "status": "busy"}}
        snap = {"live": {"state": "tool", "tool": "Bash", "updated_at": 0},
                "dead": {"state": "error", "tool": None, "updated_at": 0}}
        ids = [r["id"] for r in build_sessions(roster_map, snap)]
        self.assertIn("live", ids)
        self.assertNotIn("dead", ids)


class WispdHTTPTest(unittest.TestCase):
    def setUp(self):
        self.tmp_roster = tempfile.mkdtemp()
        self.store = SessionStore()
        self.httpd, _ = serve(port=0, store=self.store, sessions_dir=self.tmp_roster)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def _req(self, method, path, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request(method, path, body=body)
        resp = conn.getresponse()
        data = resp.read().decode("utf-8")
        conn.close()
        return resp.status, data

    def test_post_json_updates_session(self):
        body = json.dumps({"session_id": "s1", "state": "PreToolUse", "tool": "Bash"})
        status, data = self._req("POST", "/state", body)
        self.assertEqual(status, 200)
        self.assertEqual(data.strip(), protocol.TOOL)
        snap = self.store.snapshot()
        self.assertEqual(snap["s1"]["state"], protocol.TOOL)
        self.assertEqual(snap["s1"]["tool"], "Bash")

    def test_post_bare_text_is_legacy(self):
        status, data = self._req("POST", "/state", "thinking")
        self.assertEqual(status, 200)
        self.assertEqual(self.store.snapshot()["legacy"]["state"], protocol.THINKING)

    def test_post_invalid_returns_400(self):
        status, _ = self._req("POST", "/state", json.dumps({"session_id": "s", "state": "bogus"}))
        self.assertEqual(status, 400)

    def test_get_state_returns_aggregate(self):
        self._req("POST", "/state", json.dumps({"session_id": "a", "state": "idle"}))
        self._req("POST", "/state", json.dumps({"session_id": "b", "state": "tool"}))
        status, data = self._req("GET", "/state")
        self.assertEqual(status, 200)
        self.assertEqual(data.strip(), protocol.TOOL)  # 聚合:tool > idle

    def test_root_serves_html(self):
        status, data = self._req("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("AgenticWisp", data)

    def test_unknown_path_404(self):
        self.assertEqual(self._req("GET", "/nope")[0], 404)

    def test_sessions_and_aggregate_endpoints(self):
        self._req("POST", "/state", json.dumps({"session_id": "s1", "state": "thinking"}))
        status, data = self._req("GET", "/sessions")
        self.assertEqual(status, 200)
        rows = json.loads(data)
        self.assertTrue(any(r["id"] == "s1" and r["state"] == "thinking" for r in rows))
        status, agg = self._req("GET", "/aggregate")
        self.assertEqual(status, 200)
        self.assertEqual(agg.strip(), protocol.THINKING)


if __name__ == "__main__":
    unittest.main()
