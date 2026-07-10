import unittest

from agenticwisp import protocol
from agenticwisp.lamp import render


class LampRenderTest(unittest.TestCase):
    def test_tool_uses_its_truecolor_background(self):
        r, g, b = protocol.DISPLAY[protocol.TOOL]["rgb"]
        out = render(protocol.TOOL, 80, 24)
        self.assertIn(f"48;2;{r};{g};{b}", out)
        self.assertIn("TOOL", out)

    def test_idle_uses_its_truecolor_background(self):
        r, g, b = protocol.DISPLAY[protocol.IDLE]["rgb"]
        out = render(protocol.IDLE, 80, 24)
        self.assertIn(f"48;2;{r};{g};{b}", out)

    def test_clears_screen(self):
        self.assertIn("\033[2J", render(protocol.IDLE, 80, 24))

    def test_disconnected_shows_waiting(self):
        out = render(None, 80, 24, connected=False)
        self.assertIn("等待中枢", out)


if __name__ == "__main__":
    unittest.main()
