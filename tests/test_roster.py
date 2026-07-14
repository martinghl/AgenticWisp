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

    def test_skips_dead_pid_sessions(self):
        self._write("live.json", {"sessionId": "live", "cwd": "/x", "pid": os.getpid()})
        self._write("dead.json", {"sessionId": "dead", "cwd": "/x", "pid": 99999999})
        r = roster.read_roster(self.dir)
        self.assertEqual(set(r), {"live"})

    def test_keeps_sessions_without_pid(self):
        # 老版/异常写入没有 pid → 判不了死活,保留(fail-open)。
        self._write("nopid.json", {"sessionId": "np", "cwd": "/x", "name": "N"})
        self.assertEqual(set(roster.read_roster(self.dir)), {"np"})

    def test_keeps_non_int_pid(self):
        self._write("weird.json", {"sessionId": "w", "cwd": "/x", "pid": "notanumber"})
        self.assertEqual(set(roster.read_roster(self.dir)), {"w"})

    def test_missing_dir_returns_empty(self):
        self.assertEqual(roster.read_roster("/no/such/dir/xyz"), {})

    def test_keeps_huge_pid(self):
        # 超出 pid 范围的垃圾值会让 os.kill 抛 OverflowError(非 OSError)——
        # 必须 fail-open 保留,否则一个损坏的花名册文件会崩掉整个 /sessions。
        self._write("huge.json", {"sessionId": "h", "cwd": "/x", "pid": 10**20})
        self.assertEqual(set(roster.read_roster(self.dir)), {"h"})


if __name__ == "__main__":
    unittest.main()
