import unittest
from agenticwisp import protocol


class ProtocolTest(unittest.TestCase):
    def test_states_are_five(self):
        self.assertEqual(protocol.STATES, ("idle", "thinking", "tool", "waiting", "error"))

    def test_normalize_passthrough_state(self):
        self.assertEqual(protocol.normalize("tool"), protocol.TOOL)
        self.assertEqual(protocol.normalize("  idle "), protocol.IDLE)

    def test_normalize_hook_events(self):
        self.assertEqual(protocol.normalize("Stop"), protocol.IDLE)
        self.assertEqual(protocol.normalize("UserPromptSubmit"), protocol.THINKING)
        self.assertEqual(protocol.normalize("PostToolUse"), protocol.THINKING)
        self.assertEqual(protocol.normalize("PreToolUse"), protocol.TOOL)

    def test_normalize_invalid_returns_none(self):
        self.assertIsNone(protocol.normalize("garbage"))
        self.assertIsNone(protocol.normalize(None))

    def test_is_valid(self):
        self.assertTrue(protocol.is_valid("idle"))
        self.assertFalse(protocol.is_valid("PreToolUse"))

    def test_display_covers_all_states(self):
        for s in protocol.STATES:
            d = protocol.DISPLAY[s]
            self.assertIn("label", d)
            self.assertEqual(len(d["rgb"]), 3)
            self.assertTrue(d["web"].startswith("#"))
            self.assertIn("blink", d)

    def test_new_hook_events(self):
        self.assertEqual(protocol.normalize("PermissionRequest"), protocol.WAITING)
        self.assertEqual(protocol.normalize("Notification"), protocol.WAITING)
        self.assertEqual(protocol.normalize("PostToolUseFailure"), protocol.ERROR)
        self.assertEqual(protocol.normalize("StopFailure"), protocol.ERROR)

    def test_tool_is_purple(self):
        self.assertEqual(protocol.DISPLAY[protocol.TOOL]["web"], "#8b5cf6")

    def test_aggregate_priority(self):
        self.assertEqual(protocol.aggregate(["idle", "tool", "thinking"]), protocol.TOOL)
        self.assertEqual(protocol.aggregate(["tool", "error"]), protocol.ERROR)
        self.assertEqual(protocol.aggregate(["error", "waiting"]), protocol.WAITING)

    def test_aggregate_empty_is_idle(self):
        self.assertEqual(protocol.aggregate([]), protocol.IDLE)

    def test_aggregate_ignores_invalid(self):
        self.assertEqual(protocol.aggregate(["bogus", "thinking"]), protocol.THINKING)


if __name__ == "__main__":
    unittest.main()
