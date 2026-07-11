import json
import os
import tempfile
import unittest

from agenticwisp import install_hooks


class InstallHooksTest(unittest.TestCase):
    def test_build_hooks_all_events(self):
        h = install_hooks.build_hooks("/x/bin/wisp")
        self.assertEqual(set(h), {"UserPromptSubmit", "PreToolUse", "PostToolUse",
                                  "PostToolUseFailure", "PermissionRequest",
                                  "Notification", "Stop", "StopFailure",
                                  "SubagentStart", "SubagentStop"})
        # 工具类事件带 matcher,其它不带
        self.assertEqual(h["PreToolUse"][0]["matcher"], "*")
        self.assertNotIn("matcher", h["Stop"][0])
        self.assertEqual(h["Stop"][0]["hooks"][0]["command"], "/x/bin/wisp signal Stop")
        self.assertEqual(h["Stop"][0]["hooks"][0]["timeout"], 5)

    def test_merge_creates_and_is_idempotent(self):
        path = os.path.join(tempfile.mkdtemp(), "settings.json")
        added1, backup1, _ = install_hooks.merge_into_settings("/x/bin/wisp", path)
        self.assertEqual(len(added1), 10)
        self.assertIsNone(backup1)  # 无原文件 → 不备份
        with open(path) as f:
            self.assertIn("hooks", json.load(f))
        # 再跑一次:幂等,不重复添加,且这次会备份
        added2, backup2, _ = install_hooks.merge_into_settings("/x/bin/wisp", path)
        self.assertEqual(added2, [])
        self.assertTrue(backup2 and os.path.exists(backup2))

    def test_merge_preserves_existing_keys(self):
        path = os.path.join(tempfile.mkdtemp(), "settings.json")
        with open(path, "w") as f:
            json.dump({"model": "claude-x", "theme": "dark"}, f)
        install_hooks.merge_into_settings("/x/bin/wisp", path)
        with open(path) as f:
            data = json.load(f)
        self.assertEqual(data["model"], "claude-x")
        self.assertEqual(data["theme"], "dark")
        self.assertIn("hooks", data)


if __name__ == "__main__":
    unittest.main()
