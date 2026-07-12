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
        self.assertIn("waiting for hub", out)   # 默认英文

    def test_disconnected_waiting_zh(self):
        import os
        old = os.environ.get("WISP_LANG")
        os.environ["WISP_LANG"] = "zh"
        try:
            out = render(None, 80, 24, connected=False)
            self.assertIn("等待中枢", out)
        finally:
            if old is None:
                os.environ.pop("WISP_LANG", None)
            else:
                os.environ["WISP_LANG"] = old


if __name__ == "__main__":
    unittest.main()
