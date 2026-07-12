import unittest

from agenticwisp.tui import effects
from agenticwisp import palette


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
        # 够宽够高时中央是大字符画;矮面板(h<7)回退到小号单行 banner。
        # 这里测回退路径:fancy=False 无数据雨(字间空隙是真空格)且不 glitch,
        # 故可直接断言原始 banner 文本。
        grid = effects.compose_core(40, 5, "tool", 0.0, fancy=False)
        flat = self._flat(grid)
        eng, _zh = effects.banner("tool")
        self.assertIn(eng, flat)

    def test_bg_uses_state_hue(self):
        # tool 是霓虹品红(palette.state_hex=MAGENTA #ea00d9:r,b 高于 g);取一个非大字格的底色验证色相
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


class NeonHelpersTest(unittest.TestCase):
    def test_hud_title(self):
        self.assertEqual(effects.hud_title("usage"), "【 ＵＳＡＧＥ 】")

    def test_gauge(self):
        bar, color = effects.gauge(0.71, 8)
        self.assertEqual(len(bar), 8)
        self.assertEqual(bar.count("█"), 6)   # round(0.71*8)=6
        self.assertEqual(color, palette.AMBER)
        self.assertEqual(effects.gauge(0.0, 8)[0], "░" * 8)
        self.assertEqual(effects.gauge(1.0, 8)[0], "█" * 8)
        self.assertEqual(effects.gauge(None, 8)[0], "░" * 8)

    def test_scanline(self):
        # 亮线附近提亮(>1),远处奇数行轻压暗(<1)
        self.assertGreater(effects.scanline(0, 10, 0.0), 1.0)
        self.assertLessEqual(effects.scanline(5, 10, 0.0), 1.0)
        # 确定性
        self.assertEqual(effects.scanline(3, 10, 1.5), effects.scanline(3, 10, 1.5))

    def test_glitch(self):
        s = "HELLO WORLD"
        self.assertEqual(effects.glitch(s, 1.0, rate=0.0), s)     # rate 0 → 原样
        g = effects.glitch(s, 1.0, rate=1.0)
        self.assertEqual(len(g), len(s))                          # 长度不变
        self.assertEqual(g, effects.glitch(s, 1.0, rate=1.0))     # 确定性


class NeonAnimTest(unittest.TestCase):
    def test_datarain_shape_deterministic(self):
        g = effects.datarain(6, 4, 1.0)
        self.assertEqual(len(g), 4)
        self.assertTrue(all(len(row) == 6 for row in g))
        self.assertEqual(g, effects.datarain(6, 4, 1.0))          # 确定性
        # 至少有一格非空(有雨点)
        self.assertTrue(any(ch != " " for row in g for (ch, _b) in row))

    def test_energybar(self):
        bar = effects.energybar(0.5, 10, 0.0, color=palette.MAGENTA)
        self.assertEqual(len(bar), 10)
        self.assertEqual(sum(1 for ch, _c in bar if ch == "█"), 5)  # round(0.5*10)=5
        # 空段是暗轨
        self.assertTrue(all(c == palette.RAIL for ch, c in bar if ch == "░"))

    def test_neon_pulse(self):
        p = effects.neon_pulse("tool", 0.0, width=12)
        self.assertEqual(len(p), 12)
        self.assertEqual(p, effects.neon_pulse("tool", 0.0, width=12))  # 确定性
        # pulse 抬高整体
        hi = effects.neon_pulse("idle", 0.0, width=12, pulse=1.0)
        lo = effects.neon_pulse("idle", 0.0, width=12, pulse=0.0)
        self.assertGreaterEqual(sum(map(ord, hi)), sum(map(ord, lo)))


class ReactorNeonTest(unittest.TestCase):
    def test_compose_core_neon_shape(self):
        grid = effects.compose_core(30, 8, "tool", 1.0)
        self.assertEqual(len(grid), 8)
        self.assertTrue(all(len(r) == 30 for r in grid))
        # 每格结构 [char, fg|None, bg-rgb-tuple]
        ch, fg, bg = grid[0][0]
        self.assertIsInstance(bg, tuple)
        self.assertEqual(len(bg), 3)
        # 霓虹:出现过品红系(tool=MAGENTA)分量——某格 bg 的 R 明显>0 且 B 明显>0
        self.assertTrue(any(g[2][0] > 40 and g[2][2] > 40 for row in grid for g in row))
        # 顶部含单宽 HUD 标题(// STATE //);单宽避免双宽折行挤黑
        joined = "".join(g[0] for row in grid for g in row)
        self.assertIn("//", joined)
        self.assertIn("TOOL", joined)

    def test_compose_core_no_row_exceeds_terminal_width(self):
        # 每格假设占 1 终端列;任何行的显示宽度都不得超过 w,
        # 否则终端会把该行折行,把下一行挤黑(全角双宽标题就会这样)。
        import unicodedata

        def dispw(ch):
            return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1

        w = 40
        for state in ("tool", "thinking", "waiting", "idle", "error"):
            grid = effects.compose_core(w, 11, state, 0.0)
            for y, row in enumerate(grid):
                line = "".join(c[0] for c in row)
                vis = sum(dispw(ch) for ch in line)
                self.assertLessEqual(
                    vis, w,
                    f"row {y} (state={state}) 显示宽度 {vis} > w={w};含双宽字符会折行挤黑")

    def test_bigword_shape_and_bigness(self):
        rows = effects.bigword("IDLE")
        self.assertEqual(len(rows), 3)                    # 3 行高
        self.assertTrue(all(len(r) == len(rows[0]) for r in rows))  # 各行等宽
        self.assertGreater(len(rows[0]), len("IDLE"))     # 确实是"大字"(比逐字宽)
        joined = "".join(rows)
        self.assertTrue(any(c in joined for c in "▀▄█"))  # 用了半块字符

    def test_bigword_covers_all_state_letters(self):
        # 5 个状态词的每个字母都要有字模,否则渲染成空洞
        letters = set("".join(("IDLE", "THINKING", "TOOL", "WAITING", "ERROR")))
        for ch in letters:
            self.assertIn(ch, effects._BIGFONT, f"字体缺字母 {ch!r}")

    def test_bigword_font_is_single_width(self):
        # 字模只能用单宽字符,否则会重蹈标题双宽折行的覆辙
        import unicodedata
        for ch, glyph in effects._BIGFONT.items():
            for row in glyph:
                for c in row:
                    self.assertNotIn(
                        unicodedata.east_asian_width(c), ("W", "F"),
                        f"字母 {ch!r} 的字模含双宽字符 {c!r}")

    def test_compose_core_renders_bigword_when_room(self):
        # 够宽够高 → 中央是 3 行大字符画(█ 只可能来自大字)
        grid = effects.compose_core(60, 11, "idle", 0.0)
        block_rows = sum(1 for row in grid if "█" in "".join(c[0] for c in row))
        self.assertGreaterEqual(block_rows, 3, "应有 3 行大字符画")

    def test_compose_core_falls_back_when_too_narrow(self):
        # THINKING 大字宽 ~33;w=12 放不下 → 回退到小号 banner(无 █ 大字)
        grid = effects.compose_core(12, 11, "thinking", 0.0)
        self.assertEqual(len(grid), 11)
        self.assertTrue(all(len(r) == 12 for r in grid))
        block_rows = sum(1 for row in grid if "█" in "".join(c[0] for c in row))
        self.assertEqual(block_rows, 0, "窄屏应回退到小号 banner,不渲染大字")

    def test_compose_core_deterministic(self):
        self.assertEqual(effects.compose_core(20, 6, "idle", 2.0),
                         effects.compose_core(20, 6, "idle", 2.0))

    def test_compose_core_small_height_no_crash(self):
        # h=1 不应崩(HUD 标题边界检查针对实际网格)
        grid = effects.compose_core(20, 1, "tool", 0.0)
        self.assertEqual(len(grid), 1)
        self.assertEqual(len(grid[0]), 20)
        # fancy=False 路径也安全
        grid2 = effects.compose_core(20, 1, "tool", 0.0, fancy=False)
        self.assertEqual(len(grid2), 1)


if __name__ == "__main__":
    unittest.main()
