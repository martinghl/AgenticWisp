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
        self.tmp_roster = tempfile.mkdtemp()
        self.store = SessionStore()
        self.httpd, _ = serve(port=0, store=self.store, sessions_dir=self.tmp_roster)
        self.port = self.httpd.server_address[1]
        self.t = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.t.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()

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


if __name__ == "__main__":
    unittest.main()
