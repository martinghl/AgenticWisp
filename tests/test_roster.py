import json
import os
import tempfile
import unittest

from agenticwisp import roster


class RosterTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def _write(self, fn, obj):
        with open(os.path.join(self.dir, fn), "w") as f:
            json.dump(obj, f)

    def test_reads_name_cwd_status(self):
        self._write("1.json", {"sessionId": "aaa", "cwd": "/data/gli9",
                                "name": "Agentic Wisp", "status": "busy", "pid": 1})
        r = roster.read_roster(self.dir)
        self.assertEqual(r["aaa"]["name"], "Agentic Wisp")
        self.assertEqual(r["aaa"]["cwd"], "/data/gli9")
        self.assertEqual(r["aaa"]["status"], "busy")

    def test_name_falls_back_to_cwd_basename(self):
        self._write("2.json", {"sessionId": "bbb", "cwd": "/data/gli9/disease_progression"})
        r = roster.read_roster(self.dir)
        self.assertEqual(r["bbb"]["name"], "disease_progression")

    def test_name_falls_back_to_id_prefix(self):
        self._write("3.json", {"sessionId": "0123456789abcdef"})
        r = roster.read_roster(self.dir)
        self.assertEqual(r["0123456789abcdef"]["name"], "01234567")

    def test_skips_bad_files_and_missing_id(self):
        with open(os.path.join(self.dir, "bad.json"), "w") as f:
            f.write("{not json")
        self._write("noid.json", {"cwd": "/x"})
        self._write("ok.json", {"sessionId": "ccc", "cwd": "/y"})
        r = roster.read_roster(self.dir)
        self.assertEqual(set(r), {"ccc"})

    def test_skips_bg_kind_sessions(self):
        # daemon 派生的后台 job / spare 会话(kind:"bg")不是用户开的,应跳过;
        # 它们常继承母会话相同的 name+cwd,否则会在面板上显示成重复行。
        self._write("interactive.json", {"sessionId": "live", "cwd": "/data/gli9",
                                         "name": "Agentic Wisp", "kind": "interactive"})
        self._write("bg_fork.json", {"sessionId": "fork", "cwd": "/data/gli9",
                                     "name": "Agentic Wisp", "kind": "bg", "jobId": "fork"})
        self._write("bg_spare.json", {"sessionId": "spare", "cwd": "/data/gli9",
                                      "kind": "bg", "agent": "claude"})
        r = roster.read_roster(self.dir)
        self.assertEqual(set(r), {"live"})

    def test_keeps_sessions_without_kind(self):
        # 老版 Claude Code 不写 kind:denylist 只删显式 bg,缺字段的照常保留(向后兼容)。
        self._write("nokind.json", {"sessionId": "old", "cwd": "/x", "name": "Old"})
        r = roster.read_roster(self.dir)
        self.assertEqual(set(r), {"old"})

    def test_missing_dir_returns_empty(self):
        self.assertEqual(roster.read_roster("/no/such/dir/xyz"), {})


if __name__ == "__main__":
    unittest.main()
