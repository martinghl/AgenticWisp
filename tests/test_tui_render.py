import unittest

from agenticwisp import protocol
from agenticwisp.tui import render


class TuiRenderTest(unittest.TestCase):
    def test_state_hex(self):
        self.assertEqual(render.state_hex(protocol.TOOL), "#8b5cf6")
        self.assertEqual(render.state_hex("bogus"), "#333333")

    def test_breathe_period_faster_when_busy(self):
        self.assertGreater(render.breathe_period("idle"), render.breathe_period("tool"))

    def test_breathe_period_all_five_states(self):
        p = {s: render.breathe_period(s) for s in
             ("idle", "thinking", "waiting", "tool", "error")}
        self.assertEqual(p["idle"], 4.0)
        self.assertEqual(p["thinking"], 1.5)
        # 越"紧急"越快:idle > thinking > waiting > tool > error
        self.assertTrue(p["idle"] > p["thinking"] > p["waiting"] > p["tool"] >= p["error"])
        self.assertEqual(render.breathe_period("bogus"), 0.6)

    def test_brightness_gentle_range(self):
        # 柔和呼吸:摆幅小、不频闪(下限 >=0.7)
        for t in (0.0, 0.3, 0.7, 1.5, 3.9):
            b = render.brightness(t, 1.5)
            self.assertGreaterEqual(b, 0.7)
            self.assertLessEqual(b, 1.0)

    def test_build_rows(self):
        rows = render.build_rows([
            {"id": "a", "name": "Wisp", "cwd": "/home/user/project", "state": "tool", "tool": "Bash"},
            {"id": "b", "name": "X", "cwd": "/y", "state": "idle", "tool": None},
        ])
        self.assertEqual(rows[0], ("Wisp", "/home/user/project", "tool", "Bash", "#8b5cf6"))
        self.assertEqual(rows[1], ("X", "/y", "idle", "", "#22a04a"))


if __name__ == "__main__":
    unittest.main()
