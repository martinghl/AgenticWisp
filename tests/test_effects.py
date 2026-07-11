import unittest

from agenticwisp.tui import effects


class ColorFieldTest(unittest.TestCase):
    def test_shade_preserves_hue_order(self):
        # #22a04a 是 g>b>r;缩放后顺序不变
        full = effects.shade("#22a04a", 1.0)
        dark = effects.shade("#22a04a", 0.0)
        self.assertEqual(full, (34, 160, 74))
        self.assertTrue(full[1] > full[2] > full[0])
        self.assertTrue(dark[1] > dark[2] > dark[0])
        # k 越大越亮(逐通道单调不减)
        for a, b in zip(dark, full):
            self.assertLessEqual(a, b)

    def test_shade_accepts_rgb_tuple(self):
        self.assertEqual(effects.shade((100, 200, 50), 1.0), (100, 200, 50))

    def test_transition_endpoints(self):
        self.assertEqual(effects.transition_color("#000000", "#ffffff", 0.0), (0, 0, 0))
        self.assertEqual(effects.transition_color("#000000", "#ffffff", 1.0), (255, 255, 255))
        mid = effects.transition_color("#000000", "#ffffff", 0.5)
        self.assertTrue(120 <= mid[0] <= 135)

    def test_plasma_field_shape_and_range(self):
        f = effects.plasma_field(10, 4, 1.234)
        self.assertEqual(len(f), 4)
        self.assertEqual(len(f[0]), 10)
        for row in f:
            for v in row:
                self.assertGreaterEqual(v, 0.0)
                self.assertLessEqual(v, 1.0)


class GlyphTest(unittest.TestCase):
    def test_state_level(self):
        self.assertEqual(effects.state_level("idle"), 1)
        self.assertEqual(effects.state_level("error"), 6)
        self.assertTrue(effects.state_level("error") > effects.state_level("tool")
                        > effects.state_level("thinking"))
        self.assertEqual(effects.state_level("bogus"), 0)

    def test_sparkline_maps_and_pads(self):
        self.assertEqual(effects.sparkline([0, 4, 8]), " ▄█")
        self.assertEqual(effects.sparkline([100]), "█")   # 越界夹取到 8
        s = effects.sparkline([8], width=3)
        self.assertEqual(len(s), 3)
        self.assertTrue(s.endswith("█"))
        self.assertEqual(effects.sparkline([]), "")

    def test_banner_ascii_width1(self):
        eng, zh = effects.banner("tool")
        self.assertEqual(eng, "T O O L")
        self.assertEqual(zh, "调用工具")
        for s in ("idle", "thinking", "tool", "waiting", "error"):
            e, _ = effects.banner(s)
            self.assertTrue(all(ord(c) < 128 for c in e))  # 全 ASCII,宽度 1 对齐安全

    def test_particles_deterministic_and_in_bounds(self):
        a = effects.particles(2.5, 10, 30, 8)
        b = effects.particles(2.5, 10, 30, 8)
        self.assertEqual(a, b)  # 同 t 同输出
        for (x, y, ch, inten) in a:
            self.assertTrue(0 <= x < 30 and 0 <= y < 8)
            self.assertTrue(0.0 <= inten <= 1.0)


class ComposeCoreTest(unittest.TestCase):
    def _flat(self, grid):
        return "".join(cell[0] for row in grid for cell in row)

    def test_shape_and_cell_format(self):
        grid = effects.compose_core(40, 9, "tool", 0.0)
        self.assertEqual(len(grid), 9)
        self.assertTrue(all(len(row) == 40 for row in grid))
        ch, fg, bg = grid[0][0]
        self.assertIsInstance(ch, str)
        self.assertEqual(len(bg), 3)  # bg 必为 rgb 三元组

    def test_banner_text_present(self):
        grid = effects.compose_core(40, 9, "tool", 0.0)
        flat = self._flat(grid)
        for c in "TOOL":
            self.assertIn(c, flat)

    def test_bg_uses_state_hue(self):
        # tool 是紫(#8b5cf6:r,b 高于 g);取一个非大字格的底色验证色相
        grid = effects.compose_core(40, 9, "tool", 0.3)
        _, _, bg = grid[0][0]
        self.assertGreater(bg[0], bg[1])   # r > g
        self.assertGreater(bg[2], bg[1])   # b > g

    def test_degraded_has_no_particles_but_has_banner(self):
        grid = effects.compose_core(40, 9, "tool", 0.0, fancy=False)
        flat = self._flat(grid)
        for c in "TOOL":
            self.assertIn(c, flat)
        # 退化态不含粒子字符
        self.assertFalse(any(pc in flat for pc in "✦⋆∘•"))


class HeartbeatTest(unittest.TestCase):
    _BLK = " ▁▂▃▄▅▆▇█"

    def _avg(self, state):
        tot = n = 0
        for i in range(40):
            for c in effects.heartbeat(state, i * 0.1, 24):
                tot += self._BLK.index(c); n += 1
        return tot / n

    def test_length_and_charset(self):
        s = effects.heartbeat("tool", 1.0, width=12)
        self.assertEqual(len(s), 12)
        self.assertTrue(all(c in self._BLK for c in s))

    def test_deterministic(self):
        self.assertEqual(effects.heartbeat("idle", 2.5, 12, 0.3, 0.0),
                         effects.heartbeat("idle", 2.5, 12, 0.3, 0.0))

    def test_busier_is_taller_on_average(self):
        self.assertGreater(self._avg("tool"), self._avg("idle"))
        self.assertGreater(self._avg("thinking"), self._avg("idle"))

    def test_pulse_lifts_the_wave(self):
        base = sum(self._BLK.index(c) for c in effects.heartbeat("idle", 0.0, 24, 0.0, 0.0))
        lifted = sum(self._BLK.index(c) for c in effects.heartbeat("idle", 0.0, 24, 0.0, 1.0))
        self.assertGreater(lifted, base)

    def test_unknown_state_ok(self):
        self.assertEqual(len(effects.heartbeat("bogus", 1.0, 12)), 12)


if __name__ == "__main__":
    unittest.main()
