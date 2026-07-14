import http.client
import json
import os
import tempfile
import threading
import time
import unittest

from agenticwisp import protocol
from agenticwisp.wispd import SessionStore, serve, build_sessions


class BuildSessionsTest(unittest.TestCase):
    def test_joins_roster_and_details(self):
        roster_map = {"a": {"name": "Wisp", "cwd": "/data/gli9", "status": "busy"}}
        snap = {"a": {"state": "tool", "tool": "Bash", "updated_at": 0}}
        rows = build_sessions(roster_map, snap)
        self.assertEqual(rows, [{"id": "a", "name": "Wisp", "cwd": "/data/gli9",
                                 "state": "tool", "tool": "Bash", "effort": None}])

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

    def test_post_agent_id_routes_to_subagent(self):
        self._req("POST", "/state", json.dumps({"session_id": "s1", "state": "idle"}))
        self._req("POST", "/state", json.dumps({"session_id": "s1", "agent_id": "a1",
                                              "agent_type": "Explore", "state": "PreToolUse", "tool": "Grep"}))
        snap = self.store.snapshot()
        self.assertEqual(snap["s1"]["state"], protocol.IDLE)             # session 自己没被子agent改
        self.assertEqual(snap["s1"]["subagents"]["a1"]["state"], protocol.TOOL)

    def test_post_kind_stop_removes_subagent(self):
        self._req("POST", "/state", json.dumps({"session_id": "s1", "agent_id": "a1", "state": "tool"}))
        self._req("POST", "/state", json.dumps({"session_id": "s1", "agent_id": "a1", "kind": "stop"}))
        self.assertEqual(self.store.snapshot()["s1"]["subagents"], {})

    def test_aggregate_includes_subagent_state(self):
        self._req("POST", "/state", json.dumps({"session_id": "s1", "state": "idle"}))
        self._req("POST", "/state", json.dumps({"session_id": "s1", "agent_id": "a1", "state": "tool"}))
        # s1 在真实花名册外→靠 fallback 列出;子agent 的 tool 应让聚合=tool
        _, agg = self._req("GET", "/aggregate")
        self.assertEqual(agg.strip(), protocol.TOOL)


class SubagentStoreTest(unittest.TestCase):
    def test_update_subagent_and_snapshot(self):
        st = SessionStore()
        st.update("s1", "thinking")
        st.update_subagent("s1", "a1", "tool", tool="Grep", agent_type="Explore")
        snap = st.snapshot()
        self.assertEqual(snap["s1"]["state"], protocol.THINKING)         # session 自己不受影响
        sub = snap["s1"]["subagents"]["a1"]
        self.assertEqual(sub["state"], protocol.TOOL)
        self.assertEqual(sub["type"], "Explore")
        self.assertEqual(sub["tool"], "Grep")

    def test_update_session_preserves_subagents(self):
        st = SessionStore()
        st.update_subagent("s1", "a1", "tool", agent_type="Explore")
        st.update("s1", "idle")                                          # 更新 session 不应清掉子agent
        self.assertIn("a1", st.snapshot()["s1"]["subagents"])

    def test_remove_subagent(self):
        st = SessionStore()
        st.update_subagent("s1", "a1", "tool")
        st.remove_subagent("s1", "a1")
        self.assertEqual(st.snapshot()["s1"]["subagents"], {})

    def test_type_preserved_when_omitted(self):
        st = SessionStore()
        st.update_subagent("s1", "a1", "tool", agent_type="Explore")
        st.update_subagent("s1", "a1", "thinking")                       # 后续不带 type
        self.assertEqual(st.snapshot()["s1"]["subagents"]["a1"]["type"], "Explore")


class BuildSubagentsTest(unittest.TestCase):
    def test_build_includes_subagents_and_ttl(self):
        roster = {"s1": {"name": "S", "cwd": "/x", "status": "busy"}}
        snap = {"s1": {"state": "thinking", "tool": None, "updated_at": 100.0,
                       "subagents": {
                           "a1": {"type": "Explore", "state": "tool", "tool": "Grep", "updated_at": 100.0},
                           "old": {"type": "X", "state": "tool", "tool": None, "updated_at": 0.0}}}}
        rows = build_sessions(roster, snap, now=100.0, ttl=90.0)
        subs = rows[0]["subagents"]
        self.assertEqual([x["id"] for x in subs], ["a1"])                # old 超 TTL 被丢
        self.assertEqual(subs[0], {"id": "a1", "type": "Explore", "state": "tool", "tool": "Grep",
                                    "effort": None})


class ToolNameClearedTest(unittest.TestCase):
    def test_session_tool_cleared_when_not_tool_state(self):
        st = SessionStore()
        st.update("s1", "tool", "Bash")
        self.assertEqual(st.snapshot()["s1"]["tool"], "Bash")
        st.update("s1", "thinking", "Bash")          # 回到 thinking 仍带工具名
        self.assertIsNone(st.snapshot()["s1"]["tool"])

    def test_subagent_tool_cleared_when_not_tool_state(self):
        st = SessionStore()
        st.update_subagent("s1", "a1", "tool", tool="Grep", agent_type="Explore")
        self.assertEqual(st.snapshot()["s1"]["subagents"]["a1"]["tool"], "Grep")
        st.update_subagent("s1", "a1", "thinking", tool="Grep")
        self.assertIsNone(st.snapshot()["s1"]["subagents"]["a1"]["tool"])


class UsageTrackerTest(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp()
        self.proj = os.path.join(self.base, "proj")
        os.makedirs(self.proj)

    def _write(self, sid, total_tokens, mode="w"):
        line = json.dumps({"message": {"usage": {"input_tokens": total_tokens}}}) + "\n"
        with open(os.path.join(self.proj, sid + ".jsonl"), mode) as f:
            f.write(line)

    def test_tokens_accumulate(self):
        from agenticwisp.wispd import UsageTracker
        self._write("s1", 1000)
        tr = UsageTracker(self.base, min_interval=0.0)
        self.assertEqual(tr.tokens_for("s1", now=100.0), 1000)
        self._write("s1", 250, mode="a")
        self.assertEqual(tr.tokens_for("s1", now=101.0), 1250)   # 增量累加

    def test_no_transcript_returns_none(self):
        from agenticwisp.wispd import UsageTracker
        tr = UsageTracker(self.base, min_interval=0.0)
        self.assertIsNone(tr.tokens_for("ghost", now=100.0))

    def test_throttle_returns_cache(self):
        from agenticwisp.wispd import UsageTracker
        self._write("s1", 1000)
        tr = UsageTracker(self.base, min_interval=5.0)
        self.assertEqual(tr.tokens_for("s1", now=100.0), 1000)
        self._write("s1", 999, mode="a")
        self.assertEqual(tr.tokens_for("s1", now=101.0), 1000)   # 5s 内不重读
        self.assertEqual(tr.tokens_for("s1", now=200.0), 1999)   # 过限流窗后读到

    def test_prune_drops_absent_sessions(self):
        from agenticwisp.wispd import UsageTracker
        self._write("s1", 100)
        self._write("s2", 200)
        tr = UsageTracker(self.base, min_interval=0.0)
        tr.tokens_for("s1", now=100.0)
        tr.tokens_for("s2", now=100.0)
        tr.prune(["s1"])
        self.assertIn("s1", tr._st)
        self.assertNotIn("s2", tr._st)

    def test_transcript_mtime(self):
        from agenticwisp.wispd import UsageTracker
        import os
        self._write("s1", 1000)
        tr = UsageTracker(self.base, min_interval=0.0)
        self.assertIsNone(tr.transcript_mtime("s1"))    # 路径未解析前 → None
        tr.tokens_for("s1", now=100.0)                  # 触发路径解析
        os.utime(os.path.join(self.proj, "s1.jsonl"), (2500.0, 2500.0))
        self.assertEqual(tr.transcript_mtime("s1"), 2500.0)

    def test_transcript_mtime_unknown_session(self):
        from agenticwisp.wispd import UsageTracker
        tr = UsageTracker(self.base, min_interval=0.0)
        self.assertIsNone(tr.transcript_mtime("ghost"))


class SessionsTokensEndpointTest(unittest.TestCase):
    def setUp(self):
        self.tmp_roster = tempfile.mkdtemp()
        self.base = tempfile.mkdtemp()
        self.proj = os.path.join(self.base, "proj")
        os.makedirs(self.proj)
        line = json.dumps({"message": {"usage": {"input_tokens": 500, "output_tokens": 100}}}) + "\n"
        with open(os.path.join(self.proj, "s1.jsonl"), "w") as f:
            f.write(line)
        from agenticwisp.wispd import UsageTracker
        self.store = SessionStore()
        self.tracker = UsageTracker(self.base, min_interval=0.0)
        self.httpd, _ = serve(port=0, store=self.store,
                              sessions_dir=self.tmp_roster, tracker=self.tracker)
        self.port = self.httpd.server_address[1]
        self.t = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.t.start()

    def tearDown(self):
        self.httpd.shutdown(); self.httpd.server_close()

    def test_sessions_includes_tokens(self):
        self.store.update("s1", "tool", "Bash")
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2.0)
        conn.request("GET", "/sessions")
        rows = json.loads(conn.getresponse().read().decode()); conn.close()
        row = next(r for r in rows if r["id"] == "s1")
        self.assertEqual(row["tokens"], 600)


class AggregateTest(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp()
        self.proj = os.path.join(self.base, "proj")
        os.makedirs(self.proj)

    def _write(self, sid, model, inp=0, out=0, cr=0, cc=0, mode="a"):
        line = json.dumps({"message": {"model": model, "usage": {
            "input_tokens": inp, "output_tokens": out,
            "cache_read_input_tokens": cr, "cache_creation_input_tokens": cc}}}) + "\n"
        with open(os.path.join(self.proj, sid + ".jsonl"), mode) as f:
            f.write(line)

    def test_aggregate_sums_and_costs(self):
        from agenticwisp.wispd import UsageTracker
        self._write("s1", "claude-opus-4-8", inp=1_000_000)   # $5
        self._write("s2", "claude-haiku-4-5", out=1_000_000)  # $5
        tr = UsageTracker(self.base, min_interval=0.0)
        agg = tr.aggregate(["s1", "s2"], now=100.0)
        self.assertAlmostEqual(agg["cost_usd"], 10.0)
        self.assertEqual(agg["in"], 1_000_000)
        self.assertEqual(agg["out"], 1_000_000)
        self.assertEqual(agg["turns"], 2)
        self.assertEqual(agg["sessions"], 2)
        models = {r["model"] for r in agg["by_model"]}
        self.assertEqual(models, {"claude-opus-4-8", "claude-haiku-4-5"})

    def test_tokens_for_still_total(self):
        from agenticwisp.wispd import UsageTracker
        self._write("s1", "claude-opus-4-8", inp=100, out=20, cr=5)
        tr = UsageTracker(self.base, min_interval=0.0)
        self.assertEqual(tr.tokens_for("s1", now=100.0), 125)


class UsageEndpointTest(unittest.TestCase):
    def setUp(self):
        self.tmp_roster = tempfile.mkdtemp()
        self.base = tempfile.mkdtemp()
        self.proj = os.path.join(self.base, "proj")
        os.makedirs(self.proj)
        with open(os.path.join(self.proj, "s1.jsonl"), "w") as f:
            f.write(json.dumps({"message": {"model": "claude-opus-4-8",
                    "usage": {"input_tokens": 1_000_000}}}) + "\n")
        from agenticwisp.wispd import UsageTracker
        self.store = SessionStore()
        self.tracker = UsageTracker(self.base, min_interval=0.0)
        self.httpd, _ = serve(port=0, store=self.store,
                              sessions_dir=self.tmp_roster, tracker=self.tracker)
        self.port = self.httpd.server_address[1]
        self.t = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.t.start()

    def tearDown(self):
        self.httpd.shutdown(); self.httpd.server_close()

    def test_usage_endpoint(self):
        self.store.update("s1", "tool", "Bash")
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2.0)
        conn.request("GET", "/usage")
        agg = json.loads(conn.getresponse().read().decode()); conn.close()
        self.assertAlmostEqual(agg["cost_usd"], 5.0)
        self.assertEqual(agg["sessions"], 1)
        self.assertEqual(agg["by_model"][0]["model"], "claude-opus-4-8")


class EffortStoreTest(unittest.TestCase):
    def test_session_effort_stored_and_preserved(self):
        st = SessionStore()
        st.update("s1", "tool", "Bash", effort="max")
        self.assertEqual(st.snapshot()["s1"]["effort"], "max")
        st.update("s1", "thinking")  # 无 effort → 保留
        self.assertEqual(st.snapshot()["s1"]["effort"], "max")

    def test_subagent_effort_stored(self):
        st = SessionStore()
        st.update_subagent("s1", "a1", "tool", tool="Grep", agent_type="Explore", effort="low")
        self.assertEqual(st.snapshot()["s1"]["subagents"]["a1"]["effort"], "low")

    def test_build_sessions_emits_effort(self):
        roster_map = {"s1": {"name": "W", "cwd": "/x", "status": "busy"}}
        st = SessionStore(); st.update("s1", "tool", "Bash", effort="high")
        rows = build_sessions(roster_map, st.snapshot())
        self.assertEqual(rows[0]["effort"], "high")


class ModelCtxTrackerTest(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp()
        self.proj = os.path.join(self.base, "proj")
        os.makedirs(self.proj)

    def _line(self, model, inp=0, cr=0, cc=0):
        return json.dumps({"message": {"model": model, "usage": {
            "input_tokens": inp, "cache_read_input_tokens": cr,
            "cache_creation_input_tokens": cc}}}) + "\n"

    def test_session_model_ctx(self):
        from agenticwisp.wispd import UsageTracker
        with open(os.path.join(self.proj, "s1.jsonl"), "w") as f:
            f.write(self._line("claude-opus-4-8", inp=100, cr=200))
        tr = UsageTracker(self.base, min_interval=0.0)
        self.assertEqual(tr.model_ctx_for("s1", now=100.0), ("claude-opus-4-8", 300))

    def test_no_transcript_none(self):
        from agenticwisp.wispd import UsageTracker
        tr = UsageTracker(self.base, min_interval=0.0)
        self.assertEqual(tr.model_ctx_for("ghost", now=100.0), (None, None))

    def test_subagent_model_ctx(self):
        from agenticwisp.wispd import UsageTracker
        sub = os.path.join(self.proj, "s1", "subagents")
        os.makedirs(sub)
        with open(os.path.join(sub, "agent-a1.jsonl"), "w") as f:
            f.write(self._line("claude-haiku-4-5", inp=10, cr=5, cc=1))
        tr = UsageTracker(self.base, min_interval=0.0)
        self.assertEqual(tr.subagent_model_ctx("s1", "a1", now=100.0), ("claude-haiku-4-5", 16))


class SessionsModelCtxEndpointTest(unittest.TestCase):
    def setUp(self):
        self.tmp_roster = tempfile.mkdtemp()
        self.base = tempfile.mkdtemp()
        self.proj = os.path.join(self.base, "proj")
        os.makedirs(self.proj)
        with open(os.path.join(self.proj, "s1.jsonl"), "w") as f:
            f.write(json.dumps({"message": {"model": "claude-opus-4-8",
                    "usage": {"input_tokens": 700000, "cache_read_input_tokens": 0,
                              "cache_creation_input_tokens": 0}}}) + "\n")
        from agenticwisp.wispd import UsageTracker
        self.store = SessionStore()
        self.tracker = UsageTracker(self.base, min_interval=0.0)
        self.httpd, _ = serve(port=0, store=self.store,
                              sessions_dir=self.tmp_roster, tracker=self.tracker)
        self.port = self.httpd.server_address[1]
        self.t = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.t.start()

    def tearDown(self):
        self.httpd.shutdown(); self.httpd.server_close()

    def test_sessions_has_model_ctx_effort(self):
        self.store.update("s1", "tool", "Bash", effort="max")
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2.0)
        conn.request("GET", "/sessions")
        rows = json.loads(conn.getresponse().read().decode()); conn.close()
        row = next(r for r in rows if r["id"] == "s1")
        self.assertEqual(row["model"], "claude-opus-4-8")
        self.assertEqual(row["ctx_used"], 700000)
        self.assertEqual(row["ctx_max"], 1_000_000)
        self.assertEqual(row["effort"], "max")


class StaleHelperTest(unittest.TestCase):
    def test_is_stale_only_idle_and_old(self):
        from agenticwisp.wispd import _is_stale
        from agenticwisp import protocol
        self.assertTrue(_is_stale(protocol.IDLE, 100.0, 500.0, 300.0))    # 400s 旧
        self.assertFalse(_is_stale(protocol.IDLE, 100.0, 200.0, 300.0))   # 100s 新鲜
        self.assertFalse(_is_stale(protocol.TOOL, 100.0, 999.0, 300.0))   # 非 idle 永不
        self.assertFalse(_is_stale(protocol.IDLE, None, 999.0, 300.0))    # 无 transcript

    def test_stale_secs_env(self):
        import os
        from agenticwisp.wispd import _stale_secs, STALE_SECS_DEFAULT
        old = os.environ.get("WISP_STALE_SECS")
        try:
            os.environ.pop("WISP_STALE_SECS", None)
            self.assertEqual(_stale_secs(), STALE_SECS_DEFAULT)
            os.environ["WISP_STALE_SECS"] = "120"
            self.assertEqual(_stale_secs(), 120.0)
            os.environ["WISP_STALE_SECS"] = "-5"       # <=0 → 默认
            self.assertEqual(_stale_secs(), STALE_SECS_DEFAULT)
            os.environ["WISP_STALE_SECS"] = "abc"      # 非数值 → 默认
            self.assertEqual(_stale_secs(), STALE_SECS_DEFAULT)
        finally:
            if old is None:
                os.environ.pop("WISP_STALE_SECS", None)
            else:
                os.environ["WISP_STALE_SECS"] = old


class SessionsStaleFieldTest(unittest.TestCase):
    def setUp(self):
        self.tmp_roster = tempfile.mkdtemp()
        self.base = tempfile.mkdtemp()
        self.proj = os.path.join(self.base, "proj"); os.makedirs(self.proj)
        with open(os.path.join(self.proj, "s1.jsonl"), "w") as f:
            f.write(json.dumps({"message": {"usage": {"input_tokens": 500}}}) + "\n")
        from agenticwisp.wispd import UsageTracker
        self.store = SessionStore()
        self.tracker = UsageTracker(self.base, min_interval=0.0)
        self.httpd, _ = serve(port=0, store=self.store,
                              sessions_dir=self.tmp_roster, tracker=self.tracker)
        self.port = self.httpd.server_address[1]
        self.t = threading.Thread(target=self.httpd.serve_forever, daemon=True); self.t.start()

    def tearDown(self):
        self.httpd.shutdown(); self.httpd.server_close()

    def _row(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2.0)
        conn.request("GET", "/sessions")
        rows = json.loads(conn.getresponse().read().decode()); conn.close()
        return next(r for r in rows if r["id"] == "s1")

    def test_idle_old_transcript_is_stale(self):
        self.store.update("s1", "idle")
        os.utime(os.path.join(self.proj, "s1.jsonl"), (1.0, 1.0))   # 1970 → 极旧
        self.assertTrue(self._row()["stale"])

    def test_fresh_transcript_not_stale(self):
        self.store.update("s1", "idle")                            # mtime≈now
        self.assertFalse(self._row()["stale"])

    def test_tool_state_never_stale(self):
        self.store.update("s1", "tool", "Bash")
        os.utime(os.path.join(self.proj, "s1.jsonl"), (1.0, 1.0))
        self.assertFalse(self._row()["stale"])


if __name__ == "__main__":
    unittest.main()
