import asyncio
import tempfile
import threading
import unittest

from agenticwisp.wispd import SessionStore, serve

try:
    from agenticwisp.tui.app import fetch_sessions, WispApp
    HAVE_TEXTUAL = True
except Exception:
    HAVE_TEXTUAL = False


@unittest.skipUnless(HAVE_TEXTUAL, "textual 未安装")
class TuiAppTest(unittest.TestCase):
    def setUp(self):
        # Python 3.9: textual widgets grab the current asyncio loop at construction
        # (via asyncio.Lock), and asyncio.run() in the run_test-based tests leaves the
        # current loop cleared — so give every test a fresh current loop for any bare
        # widget construction. Harmless on 3.10+ (run_test uses its own loop).
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self.tmp_roster = tempfile.mkdtemp()
        self.tmp_projects = tempfile.mkdtemp()
        self.store = SessionStore()
        from agenticwisp.wispd import UsageTracker
        self.tracker = UsageTracker(self.tmp_projects, min_interval=0.0)
        self.httpd, _ = serve(port=0, store=self.store,
                              sessions_dir=self.tmp_roster, tracker=self.tracker)
        self.port = self.httpd.server_address[1]
        self.t = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.t.start()

    def _write_transcript(self, sid, usages, mode="a"):
        import os as _os, json as _json
        proj = _os.path.join(self.tmp_projects, "proj")
        _os.makedirs(proj, exist_ok=True)
        with open(_os.path.join(proj, sid + ".jsonl"), mode) as f:
            for u in usages:
                u = dict(u)
                model = u.pop("model", None)
                msg = {"usage": u}
                if model is not None:
                    msg["model"] = model
                f.write(_json.dumps({"message": msg}) + "\n")

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        if not self._loop.is_closed():
            self._loop.close()
        asyncio.set_event_loop(None)

    def test_fetch_sessions(self):
        self.store.update("s1", "tool", "Bash")
        rows = fetch_sessions("127.0.0.1", self.port, timeout=2.0)
        self.assertTrue(any(r["id"] == "s1" for r in rows))

    def test_app_mounts(self):
        app = WispApp(host="127.0.0.1", port=self.port)
        async def run():
            async with app.run_test() as pilot:
                await pilot.pause()
        import asyncio
        asyncio.run(run())

    def test_reactor_and_heartbeat_mount(self):
        self.store.update("s1", "tool", "Bash")
        self.store.update("s2", "thinking")
        app = WispApp(host="127.0.0.1", port=self.port)
        async def run():
            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.pause()
        import asyncio
        asyncio.run(run())

    def test_subagent_subrows_mount(self):
        self.store.update("s1", "thinking")
        self.store.update_subagent("s1", "a1", "tool", tool="Grep", agent_type="Explore")
        app = WispApp(host="127.0.0.1", port=self.port)
        async def run():
            async with app.run_test() as pilot:
                app.refresh_state(); await pilot.pause()
                app.animate_heartbeats(); await pilot.pause()
                # 父 s1 + 子 a1 各占一行(2 行),数字键仍只选父
                self.assertIn("s1", app._session_ids)
                self.assertNotIn("s1\x00a1", app._session_ids)
                # 真正验证子行被渲染:表里有子行、_rows 含其状态、名字列是 ↳ 类型
                table = app.query_one("#table")
                self.assertEqual(table.row_count, 2)
                self.assertIn(("s1\x00a1", "tool", False), app._rows)
                self.assertIn("Explore", table.get_row("s1\x00a1")[1])
        import asyncio
        asyncio.run(run())

    def test_time_and_token_columns(self):
        self.store.update("s1", "tool", "Bash")
        self._write_transcript("s1", [{"input_tokens": 120000}])
        app = WispApp(host="127.0.0.1", port=self.port)
        async def run():
            async with app.run_test() as pilot:
                app.refresh_state(); await pilot.pause()
                app.animate_heartbeats(); await pilot.pause()
                table = app.query_one("#table")
                labels = [str(c.label) for c in table.columns.values()]
                self.assertIn("time", labels)
                self.assertIn("token", labels)
                row = table.get_row("s1")
                self.assertEqual(str(row[8]), "120k")     # token 列(第 9 列,索引8)
                self.assertTrue(str(row[7]))               # time 列非空

                # 证明 animate_heartbeats 更新了 time 列(不仅是 refresh_state):
                # 将上次变化时间设为 ~1h 前,然后单独调用 animate_heartbeats,
                # 验证 time 列现在显示 "1h" 开头的值(只有 animate_heartbeats 能写入这个值)
                app._last_change["s1"] -= 3700  # 假装该状态已持续 ~1h
                app.animate_heartbeats(); await pilot.pause()
                row_updated = table.get_row("s1")
                time_str = str(row_updated[7])
                self.assertTrue(time_str.startswith("1h"),
                               f"Expected time to start with '1h', got '{time_str}'")
        import asyncio
        asyncio.run(run())

    def test_subagent_row_token_dash(self):
        """验证子行 token 列显示 '—'(不显示实数)。"""
        self.store.update("s1", "thinking")
        self.store.update_subagent("s1", "a1", "tool", tool="Grep", agent_type="Explore")
        app = WispApp(host="127.0.0.1", port=self.port)
        async def run():
            async with app.run_test() as pilot:
                app.refresh_state(); await pilot.pause()
                table = app.query_one("#table")
                # 子行的 row_key 格式为 "s1\x00a1"
                sub_row = table.get_row("s1\x00a1")
                self.assertEqual(str(sub_row[8]), "—",
                                f"Expected sub-row token to be '—', got '{str(sub_row[8])}'")
        import asyncio
        asyncio.run(run())

    def test_token_pulse_decays_and_skips_subrows(self):
        import agenticwisp.tui.app as appmod
        app = WispApp(host="127.0.0.1", port=self.port)
        app._token_surge["s1"] = 1.0
        app._token_surge_at["s1"] = 100.0
        self.assertAlmostEqual(app._token_pulse("s1", 100.0), 1.0, places=6)
        self.assertEqual(app._token_pulse("s1", 100.0 + appmod._TOKEN_PULSE_DECAY), 0.0)
        self.assertEqual(app._token_pulse("s1\x00a1", 100.0), 0.0)   # 子行不吃

    def test_token_growth_triggers_surge(self):
        self.store.update("s1", "thinking")
        self._write_transcript("s1", [{"input_tokens": 500}])
        app = WispApp(host="127.0.0.1", port=self.port)
        async def run():
            async with app.run_test() as pilot:
                app.refresh_state(); await pilot.pause()               # 首次:记初值,无涌动
                self.assertEqual(app._token_surge.get("s1", 0.0), 0.0)
                self._write_transcript("s1", [{"input_tokens": 60000}])  # token 猛涨
                app.refresh_state(); await pilot.pause()
                self.assertGreater(app._token_surge.get("s1", 0.0), 0.0)
        import asyncio
        asyncio.run(run())

    def _write_usage_line(self, sid, model, inp=0, out=0, cr=0, cc=0):
        import os as _os, json as _json
        proj = _os.path.join(self.tmp_projects, "proj")
        _os.makedirs(proj, exist_ok=True)
        with open(_os.path.join(proj, sid + ".jsonl"), "a") as f:
            f.write(_json.dumps({"message": {"model": model, "usage": {
                "input_tokens": inp, "output_tokens": out,
                "cache_read_input_tokens": cr, "cache_creation_input_tokens": cc}}}) + "\n")

    def test_usage_hud_renders(self):
        self.store.update("s1", "tool", "Bash")
        self._write_transcript("s1", [{"model": "claude-opus-4-8", "input_tokens": 300000,
                                       "output_tokens": 12000, "cache_read_input_tokens": 0,
                                       "cache_creation_input_tokens": 0}])
        app = WispApp(host="127.0.0.1", port=self.port)
        async def run():
            async with app.run_test() as pilot:
                app.refresh_state(); await pilot.pause()
                panel = app.query_one("#dash")
                s = panel.renderable.plain if hasattr(panel.renderable, "plain") else str(panel.renderable)
                self.assertIn("USAGE", s)
                self.assertIn("$", s)
                self.assertIn("opus-4-8", s)
        import asyncio
        asyncio.run(run())

    def test_usage_hud_placeholder(self):
        from agenticwisp.tui.app import UsageHUD
        self.assertIn("waiting", UsageHUD()._render_text().plain)

    def test_neon_row_columns(self):
        self.store.update("s1", "tool", "Bash", effort="max")
        self._write_transcript("s1", [{"model": "claude-opus-4-8",
                                       "input_tokens": 700000,
                                       "cache_read_input_tokens": 0,
                                       "cache_creation_input_tokens": 0}])
        app = WispApp(host="127.0.0.1", port=self.port)
        async def run():
            async with app.run_test() as pilot:
                app.refresh_state(); await pilot.pause()
                app.animate_heartbeats(); await pilot.pause()
                table = app.query_one("#table")
                labels = [str(c.label) for c in table.columns.values()]
                self.assertIn("model", labels)
                self.assertIn("effort", labels)
                self.assertIn("ctx", labels)
                self.assertNotIn("cwd", labels)
                self.assertIn("state", labels)   # 列头默认英文
                self.assertNotIn("状态", labels)
                row = table.get_row("s1")
                joined = " ".join(str(c) for c in row)
                self.assertIn("opus-4-8", joined)
                self.assertIn("max", joined)
        import asyncio
        asyncio.run(run())

    def test_stale_row_shows_pause_marker(self):
        import os as _os
        self.store.update("s1", "idle")
        self._write_transcript("s1", [{"input_tokens": 100}])
        proj = _os.path.join(self.tmp_projects, "proj")
        _os.utime(_os.path.join(proj, "s1.jsonl"), (1.0, 1.0))   # 极旧 → stale
        app = WispApp(host="127.0.0.1", port=self.port)
        async def run():
            async with app.run_test() as pilot:
                app.refresh_state(); await pilot.pause()
                row = app.query_one("#table").get_row("s1")
                self.assertIn("⏸", str(row[3]))                 # state 列(索引3)
        import asyncio
        asyncio.run(run())

    def test_active_row_no_pause_marker(self):
        self.store.update("s1", "tool", "Bash")
        app = WispApp(host="127.0.0.1", port=self.port)
        async def run():
            async with app.run_test() as pilot:
                app.refresh_state(); await pilot.pause()
                row = app.query_one("#table").get_row("s1")
                self.assertNotIn("⏸", str(row[3]))
                self.assertIn("●", str(row[3]))
        import asyncio
        asyncio.run(run())

    def test_stale_row_fully_muted(self):
        import os as _os
        from agenticwisp import palette
        self.store.update("s1", "idle")
        self._write_transcript("s1", [{"input_tokens": 100}])
        proj = _os.path.join(self.tmp_projects, "proj")
        _os.utime(_os.path.join(proj, "s1.jsonl"), (1.0, 1.0))   # 极旧 → stale
        app = WispApp(host="127.0.0.1", port=self.port)
        async def run():
            async with app.run_test() as pilot:
                app.refresh_state(); await pilot.pause()
                app.animate_heartbeats(); await pilot.pause()   # 证明 animate 后 heart/time 仍 MUTED
                table = app.query_one("#table")
                row = table.get_row("s1")
                # 列: 0#,1session,2model,3state,4effort,5ctx,6heart,7time,8token
                for i in (3, 4, 5, 6, 7):
                    self.assertEqual(row[i].style, palette.MUTED,
                                     f"stale 行第 {i} 列应为 MUTED, 实际 {row[i].style!r}")
        import asyncio
        asyncio.run(run())

    def test_active_row_heart_not_muted(self):
        from agenticwisp import palette
        self.store.update("s1", "tool", "Bash")
        app = WispApp(host="127.0.0.1", port=self.port)
        async def run():
            async with app.run_test() as pilot:
                app.refresh_state(); await pilot.pause()
                app.animate_heartbeats(); await pilot.pause()
                table = app.query_one("#table")
                row = table.get_row("s1")
                self.assertEqual(row[6].style, palette.state_hex("tool"))   # heart 用状态色
                self.assertNotEqual(row[6].style, palette.MUTED)
        import asyncio
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
