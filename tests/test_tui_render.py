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
            {"id": "a", "name": "Wisp", "cwd": "/data/gli9", "state": "tool", "tool": "Bash"},
            {"id": "b", "name": "X", "cwd": "/y", "state": "idle", "tool": None},
        ])
        self.assertEqual(rows[0], ("Wisp", "/data/gli9", "tool", "Bash", "#8b5cf6"))
        self.assertEqual(rows[1], ("X", "/y", "idle", "", "#22a04a"))


class FormatHelpersTest(unittest.TestCase):
    def test_fmt_duration(self):
        self.assertEqual(render.fmt_duration(8), "8s")
        self.assertEqual(render.fmt_duration(0), "0s")
        self.assertEqual(render.fmt_duration(134), "2m14s")
        self.assertEqual(render.fmt_duration(3720), "1h2m")

    def test_fmt_tokens(self):
        self.assertEqual(render.fmt_tokens(None), "—")
        self.assertEqual(render.fmt_tokens(999), "999")
        self.assertEqual(render.fmt_tokens(312000), "312k")
        self.assertEqual(render.fmt_tokens(1240000), "1.24M")

    def test_short_cwd(self):
        self.assertEqual(render.short_cwd("/data/gli9"), "gli9")
        self.assertEqual(render.short_cwd("/data/gli9/"), "gli9")
        self.assertEqual(render.short_cwd("/"), "/")
        self.assertEqual(render.short_cwd(""), "")


class CostAndModelTest(unittest.TestCase):
    def test_fmt_cost(self):
        self.assertEqual(render.fmt_cost(0), "$0.00")
        self.assertEqual(render.fmt_cost(0.004), "<$0.01")
        self.assertEqual(render.fmt_cost(12.47), "$12.47")
        self.assertEqual(render.fmt_cost(1200), "$1.2k")

    def test_short_model(self):
        self.assertEqual(render.short_model("claude-opus-4-8"), "opus-4-8")
        self.assertEqual(render.short_model("<synthetic>"), "<synthetic>")
        self.assertEqual(render.short_model(""), "?")


if __name__ == "__main__":
    unittest.main()
