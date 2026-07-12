import http.client
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
    def test_reads_all_fields(self):
        s = io.StringIO(json.dumps({"session_id": "abc", "tool_name": "Bash",
                                    "agent_id": "a1", "agent_type": "Explore"}))
        ctx = read_stdin_context(s)
        self.assertEqual(ctx["session_id"], "abc")
        self.assertEqual(ctx["tool"], "Bash")
        self.assertEqual(ctx["agent_id"], "a1")
        self.assertEqual(ctx["agent_type"], "Explore")

    def test_empty_and_bad(self):
        self.assertEqual(read_stdin_context(io.StringIO("")), {})
        self.assertEqual(read_stdin_context(io.StringIO("{bad")), {})


class SignalNoHubTest(unittest.TestCase):
    def test_send_returns_none_when_no_hub(self):
        self.assertIsNone(send("tool", port=DEAD_PORT, timeout=0.2))

    def test_send_invalid_state_returns_none(self):
        self.assertIsNone(send("garbage", port=DEAD_PORT, timeout=0.2))

    def test_main_returns_zero_even_without_hub(self):
        os.environ["WISP_PORT"] = str(DEAD_PORT)
        try:
            self.assertEqual(main(["tool"]), 0)
            self.assertEqual(main(["SubagentStart"]), 0)
            self.assertEqual(main(["SubagentStop"]), 0)
        finally:
            del os.environ["WISP_PORT"]

    def test_main_returns_zero_on_malformed_port(self):
        os.environ["WISP_PORT"] = "not_a_number"
        try:
            self.assertEqual(main(["tool"]), 0)
        finally:
            del os.environ["WISP_PORT"]


class EffortTest(unittest.TestCase):
    def test_reads_effort_level(self):
        import io
        ctx = read_stdin_context(io.StringIO(json.dumps({
            "session_id": "s1", "tool_name": "Bash", "effort": {"level": "max"}})))
        self.assertEqual(ctx["effort"], "max")

    def test_effort_absent(self):
        import io
        ctx = read_stdin_context(io.StringIO(json.dumps({"session_id": "s1"})))
        self.assertIsNone(ctx.get("effort"))


class SignalWithHubTest(unittest.TestCase):
    def setUp(self):
        self.tmp = __import__("tempfile").mkdtemp()
        self.store = SessionStore()
        self.httpd, _ = serve(port=0, store=self.store, sessions_dir=self.tmp)
        self.port = self.httpd.server_address[1]
        self.t = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.t.start()
        os.environ["WISP_PORT"] = str(self.port)

    def tearDown(self):
        del os.environ["WISP_PORT"]
        self.httpd.shutdown(); self.httpd.server_close()

    def _feed(self, event, payload):
        import sys
        old = sys.stdin
        sys.stdin = io.StringIO(json.dumps(payload))
        try:
            main([event])
        finally:
            sys.stdin = old

    def test_session_event_updates_session(self):
        self._feed("PreToolUse", {"session_id": "s1", "tool_name": "Bash"})
        self.assertEqual(self.store.snapshot()["s1"]["state"], protocol.TOOL)

    def test_ask_user_maps_to_waiting_not_tool(self):
        # Claude 问用户(AskUserQuestion)经 PreToolUse 上报,但语义是"等你"→ waiting,不是 tool
        self._feed("PreToolUse", {"session_id": "s1", "tool_name": "AskUserQuestion"})
        self.assertEqual(self.store.snapshot()["s1"]["state"], protocol.WAITING)

    def test_exit_plan_mode_maps_to_waiting(self):
        self._feed("PreToolUse", {"session_id": "s1", "tool_name": "ExitPlanMode"})
        self.assertEqual(self.store.snapshot()["s1"]["state"], protocol.WAITING)

    def test_subagent_event_updates_subagent(self):
        self._feed("PreToolUse", {"session_id": "s1", "agent_id": "a1",
                                  "agent_type": "Explore", "tool_name": "Grep"})
        sub = self.store.snapshot()["s1"]["subagents"]["a1"]
        self.assertEqual(sub["state"], protocol.TOOL)
        self.assertEqual(sub["type"], "Explore")

    def test_subagent_start_and_stop(self):
        self._feed("SubagentStart", {"session_id": "s1", "agent_id": "a1", "agent_type": "Plan"})
        self.assertIn("a1", self.store.snapshot()["s1"]["subagents"])
        self._feed("SubagentStop", {"session_id": "s1", "agent_id": "a1"})
        self.assertNotIn("a1", self.store.snapshot()["s1"]["subagents"])


if __name__ == "__main__":
    unittest.main()
