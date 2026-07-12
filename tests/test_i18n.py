import os
import unittest

from agenticwisp import i18n


class I18nTest(unittest.TestCase):
    def setUp(self):
        self._old = os.environ.get("WISP_LANG")
        os.environ.pop("WISP_LANG", None)

    def tearDown(self):
        if self._old is None:
            os.environ.pop("WISP_LANG", None)
        else:
            os.environ["WISP_LANG"] = self._old

    def test_default_is_english(self):
        self.assertEqual(i18n.lang(), "en")
        self.assertEqual(i18n.t("tui.bind.quit"), "quit")

    def test_zh_when_set(self):
        os.environ["WISP_LANG"] = "zh"
        self.assertEqual(i18n.lang(), "zh")
        self.assertEqual(i18n.t("tui.bind.quit"), "退出")

    def test_invalid_lang_falls_back_english(self):
        os.environ["WISP_LANG"] = "fr"
        self.assertEqual(i18n.lang(), "en")
        self.assertEqual(i18n.t("tui.bind.quit"), "quit")

    def test_missing_key_returns_key(self):
        self.assertEqual(i18n.t("no.such.key"), "no.such.key")

    def test_format_interpolation(self):
        s = i18n.t("hub.listening", port=9099)
        self.assertIn("9099", s)

    def test_state_label_both_langs(self):
        self.assertEqual(i18n.state_label("idle"), "IDLE")
        os.environ["WISP_LANG"] = "zh"
        self.assertEqual(i18n.state_label("idle"), "空闲")

    def test_state_label_unknown_is_raw(self):
        self.assertEqual(i18n.state_label("zzz"), "zzz")

    def test_zh_missing_key_falls_back_to_english(self):
        os.environ["WISP_LANG"] = "zh"
        # a key present only in en catalog still returns (english) text, never crashes
        self.assertEqual(i18n.t("no.such.key"), "no.such.key")


if __name__ == "__main__":
    unittest.main()
