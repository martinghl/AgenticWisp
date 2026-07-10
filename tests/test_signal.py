import io
import json
import os
import threading
import unittest

from agenticwisp import protocol
from agenticwisp.signal import send, main, read_stdin_context
from agenticwisp.wispd import SessionStore, serve

DEAD_PORT = 59999


class StdinContextTest(unittest.TestCase):
    def test_reads_session_and_tool(self):
        s = io.StringIO(json.dumps({"session_id": "abc", "tool_name": "Bash"}))
        self.assertEqual(read_stdin_context(s), ("abc", "Bash"))

    def test_empty_stdin(self):
        self.assertEqual(read_stdin_context(io.StringIO("")), (None, None))

    def test_bad_json(self):
        self.assertEqual(read_stdin_context(io.StringIO("{not json")), (None, None))


class SignalNoHubTest(unittest.TestCase):
    def test_send_returns_none_when_no_hub(self):
        self.assertIsNone(send("tool", port=DEAD_PORT, timeout=0.2))

    def test_main_returns_zero_even_without_hub(self):
        os.environ["WISP_PORT"] = str(DEAD_PORT)
        try:
            self.assertEqual(main(["tool"]), 0)
        finally:
            del os.environ["WISP_PORT"]

    def test_send_invalid_state_returns_none(self):
        self.assertIsNone(send("garbage", port=DEAD_PORT, timeout=0.2))

    def test_main_returns_zero_on_malformed_port(self):
        os.environ["WISP_PORT"] = "not_a_number"
        try:
            self.assertEqual(main(["tool"]), 0)
        finally:
            del os.environ["WISP_PORT"]


class SignalWithHubTest(unittest.TestCase):
    def setUp(self):
        self.store = SessionStore()
        self.httpd, _ = serve(port=0, store=self.store)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def test_send_updates_named_session(self):
        result = send("PreToolUse", session_id="sid9", tool="Bash", port=self.port, timeout=1.0)
        self.assertEqual(result, protocol.TOOL)
        snap = self.store.snapshot()
        self.assertEqual(snap["sid9"]["state"], protocol.TOOL)
        self.assertEqual(snap["sid9"]["tool"], "Bash")


if __name__ == "__main__":
    unittest.main()
