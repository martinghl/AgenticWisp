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

    def test_render_page_english_by_default(self):
        from agenticwisp import page
        html = page.render_page()
        self.assertIn('<html lang="en">', html)
        self.assertIn("click a card to focus", html)
        self.assertIn("waiting for hub", html)
        self.assertIn("IDLE", html)          # 状态标签英文
        self.assertNotIn("点卡片专注", html)

    def test_render_page_chinese_when_set(self):
        import os
        from agenticwisp import page
        old = os.environ.get("WISP_LANG")
        os.environ["WISP_LANG"] = "zh"
        try:
            html = page.render_page()
            self.assertIn('<html lang="zh">', html)
            self.assertIn("点卡片专注", html)
            self.assertIn("空闲", html)
        finally:
            if old is None:
                os.environ.pop("WISP_LANG", None)
            else:
                os.environ["WISP_LANG"] = old

    def test_stale_card_class_present(self):
        html = render_page()
        self.assertIn(".card.stale", html)   # CSS 规则存在
        self.assertIn("s.stale", html)       # JS 读取 stale 字段


if __name__ == "__main__":
    unittest.main()
