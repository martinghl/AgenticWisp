import unittest

from agenticwisp import palette, protocol


class PaletteTest(unittest.TestCase):
    def test_state_hex(self):
        self.assertEqual(palette.state_hex(protocol.IDLE), palette.CYAN)
        self.assertEqual(palette.state_hex(protocol.TOOL), palette.MAGENTA)
        self.assertEqual(palette.state_hex(protocol.ERROR), palette.PINK)
        self.assertEqual(palette.state_hex("nonsense"), palette.RAIL)

    def test_ctx_color(self):
        self.assertEqual(palette.ctx_color(None), palette.RAIL)
        self.assertEqual(palette.ctx_color(0.3), palette.CYAN)
        self.assertEqual(palette.ctx_color(0.7), palette.AMBER)
        self.assertEqual(palette.ctx_color(0.9), palette.PINK)

    def test_effort_color(self):
        self.assertEqual(palette.effort_color("max"), palette.PINK)
        self.assertEqual(palette.effort_color("high"), palette.GREEN)
        self.assertEqual(palette.effort_color(None), palette.RAIL)
