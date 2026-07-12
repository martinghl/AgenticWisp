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


class RemoveHooksTest(unittest.TestCase):
    def _settings(self, data):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "settings.json")
        with open(p, "w") as f:
            json.dump(data, f)
        return p

    def test_remove_deletes_our_hooks_keeps_others(self):
        p = self._settings({})
        install_hooks.merge_into_settings("/abs/bin/wisp", settings_path=p)
        with open(p) as f:
            data = json.load(f)
        data["hooks"]["Stop"].append(
            {"hooks": [{"type": "command", "command": "/other/tool notify", "timeout": 5}]})
        with open(p, "w") as f:
            json.dump(data, f)

        removed, backup, _ = install_hooks.remove_from_settings(settings_path=p)

        self.assertTrue(removed)
        self.assertIsNotNone(backup)
        with open(p) as f:
            out = json.load(f)
        blob = json.dumps(out)
        self.assertNotIn("/abs/bin/wisp", blob)      # our commands gone
        self.assertIn("/other/tool notify", blob)     # unrelated hook kept

    def test_remove_is_idempotent(self):
        p = self._settings({})
        install_hooks.merge_into_settings("/abs/bin/wisp", settings_path=p)
        install_hooks.remove_from_settings(settings_path=p)
        removed2, _, _ = install_hooks.remove_from_settings(settings_path=p)
        self.assertEqual(removed2, [])

    def test_remove_keeps_unrelated_command_bundled_in_same_group(self):
        p = self._settings({"hooks": {"Stop": [
            {"hooks": [
                {"type": "command", "command": "/abs/bin/wisp signal Stop", "timeout": 5},
                {"type": "command", "command": "/other/tool notify", "timeout": 5},
            ]}
        ]}})
        install_hooks.remove_from_settings(settings_path=p)
        with open(p) as f:
            blob = json.dumps(json.load(f))
        self.assertNotIn("/abs/bin/wisp", blob)
        self.assertIn("/other/tool notify", blob)

    def test_is_ours_matches_launcher_signal_event(self):
        self.assertTrue(install_hooks._is_ours("/home/u/.local/bin/wisp signal Stop", "Stop"))
        self.assertTrue(install_hooks._is_ours("/repo/bin/wisp signal PreToolUse", "PreToolUse"))
        self.assertFalse(install_hooks._is_ours("/other/tool notify Stop", "Stop"))
        self.assertFalse(install_hooks._is_ours("/repo/bin/wisp signal Stop", "PreToolUse"))

    def test_is_ours_matches_env_prefixed_snippet_form(self):
        self.assertTrue(install_hooks._is_ours(
            "WISP_PYTHON=/usr/bin/python3 /data/x/bin/wisp signal Stop", "Stop"))
        self.assertFalse(install_hooks._is_ours(
            "/opt/agenticwisp.signal-x/tool signal Stop", "Stop"))

    def test_remove_strips_env_prefixed_snippet_form(self):
        p = self._settings({"hooks": {"Stop": [
            {"hooks": [{"type": "command",
                        "command": "WISP_PYTHON=/usr/bin/python3 /data/x/bin/wisp signal Stop",
                        "timeout": 5}]}
        ]}})
        removed, _b, _p = install_hooks.remove_from_settings(settings_path=p)
        self.assertIn("Stop", removed)
        with open(p) as f:
            self.assertNotIn("/data/x/bin/wisp", json.dumps(json.load(f)))


if __name__ == "__main__":
    unittest.main()
