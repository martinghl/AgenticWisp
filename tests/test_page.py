import unittest

from agenticwisp import protocol
from agenticwisp.page import render_page


class PageTest(unittest.TestCase):
    def test_contains_title(self):
        self.assertIn("AgenticWisp", render_page())

    def test_contains_each_state_color(self):
        html = render_page()
        for s in protocol.STATES:
            self.assertIn(protocol.DISPLAY[s]["web"], html)

    def test_fetches_sessions_endpoint(self):
        self.assertIn("/sessions", render_page())

    def test_poll_interval_injected(self):
        self.assertIn('"poll": 500', render_page(poll_ms=500))

    def test_is_html_document(self):
        self.assertTrue(render_page().lstrip().lower().startswith("<!doctype html"))


if __name__ == "__main__":
    unittest.main()
