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
        self._write("1.json", {"sessionId": "aaa", "cwd": "/home/user/project",
                                "name": "Agentic Wisp", "status": "busy", "pid": 1})
        r = roster.read_roster(self.dir)
        self.assertEqual(r["aaa"]["name"], "Agentic Wisp")
        self.assertEqual(r["aaa"]["cwd"], "/home/user/project")
        self.assertEqual(r["aaa"]["status"], "busy")

    def test_name_falls_back_to_cwd_basename(self):
        self._write("2.json", {"sessionId": "bbb", "cwd": "/home/user/project/data-pipeline"})
        r = roster.read_roster(self.dir)
        self.assertEqual(r["bbb"]["name"], "data-pipeline")

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

    def test_missing_dir_returns_empty(self):
        self.assertEqual(roster.read_roster("/no/such/dir/xyz"), {})


if __name__ == "__main__":
    unittest.main()
