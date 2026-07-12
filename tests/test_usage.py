import json
import os
import tempfile
import unittest

from agenticwisp import usage


def _line(inp=0, out=0, cr=0, cc=0):
    return json.dumps({"type": "assistant",
                       "message": {"usage": {"input_tokens": inp, "output_tokens": out,
                                             "cache_read_input_tokens": cr,
                                             "cache_creation_input_tokens": cc}}}) + "\n"


class FindTranscriptTest(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp()

    def test_finds_by_session_id(self):
        proj = os.path.join(self.base, "-data-x")
        os.makedirs(proj)
        p = os.path.join(proj, "sid123.jsonl")
        open(p, "w").close()
        self.assertEqual(usage.find_transcript("sid123", self.base), p)

    def test_missing_returns_none(self):
        self.assertIsNone(usage.find_transcript("nope", self.base))
        self.assertIsNone(usage.find_transcript("", self.base))


class ScanUsageTest(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "t.jsonl")

    def _write(self, text, mode="w"):
        with open(self.path, mode) as f:
            f.write(text)

    def test_full_read_sums_all_usage(self):
        self._write(_line(100, 10, 5, 0) + _line(200, 20, 0, 3))
        added, off = usage.scan_usage(self.path, 0)
        self.assertEqual(added, 100 + 10 + 5 + 200 + 20 + 3)
        self.assertEqual(off, os.path.getsize(self.path))

    def test_incremental_only_reads_new(self):
        self._write(_line(100))
        _, off = usage.scan_usage(self.path, 0)
        self._write(_line(50), mode="a")
        added, off2 = usage.scan_usage(self.path, off)
        self.assertEqual(added, 50)
        self.assertEqual(off2, os.path.getsize(self.path))

    def test_partial_last_line_not_consumed(self):
        self._write(_line(100))
        _, off = usage.scan_usage(self.path, 0)
        self._write('{"message": {"usage": {"output_tokens": 7', mode="a")  # 无换行的半行
        added, off2 = usage.scan_usage(self.path, off)
        self.assertEqual(added, 0)
        self.assertEqual(off2, off)              # 不越过半行
        self._write('0}}}\n', mode="a")           # 补全该行
        added2, _ = usage.scan_usage(self.path, off2)
        self.assertEqual(added2, 70)

    def test_truncation_resets(self):
        self._write(_line(100) + _line(200))
        _, off = usage.scan_usage(self.path, 0)
        self._write(_line(9))                     # 覆盖重写,文件变短
        added, off2 = usage.scan_usage(self.path, off)   # off 比新文件还大
        self.assertEqual(added, 9)
        self.assertEqual(off2, os.path.getsize(self.path))

    def test_bad_json_line_skipped(self):
        self._write("not json\n" + _line(42))
        added, _ = usage.scan_usage(self.path, 0)
        self.assertEqual(added, 42)

    def test_missing_file(self):
        self.assertEqual(usage.scan_usage("/no/such/file.jsonl", 0), (0, 0))

    def test_iterations_excluded_and_missing_keys_default_to_zero(self):
        """iterations 被忽略,缺失的 cache 键默认为 0."""
        line = json.dumps({"type": "assistant",
                          "message": {"usage": {"input_tokens": 100, "output_tokens": 20,
                                                "iterations": [{"input_tokens": 999}]}}}) + "\n"
        self._write(line)
        added, _ = usage.scan_usage(self.path, 0)
        self.assertEqual(added, 120)  # 100 + 20, iterations ignored, missing cache keys → 0

    def test_malformed_usage_value_does_not_raise(self):
        """畸形 usage 值(如 "N/A") 不抛,被强制为 0."""
        line = json.dumps({"type": "assistant",
                          "message": {"usage": {"input_tokens": "N/A", "output_tokens": 5}}}) + "\n"
        self._write(line)
        added, size = usage.scan_usage(self.path, 0)
        self.assertEqual(added, 5)  # "N/A" coerces to 0, output 5 still counts
        self.assertEqual(size, os.path.getsize(self.path))


class ScanDetailedTest(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "t.jsonl")

    def _write(self, text, mode="w"):
        with open(self.path, mode) as f:
            f.write(text)

    def _line(self, model, inp=0, out=0, cr=0, cc=0, ws=0, wf=0):
        return json.dumps({"message": {"model": model, "usage": {
            "input_tokens": inp, "output_tokens": out,
            "cache_read_input_tokens": cr, "cache_creation_input_tokens": cc,
            "server_tool_use": {"web_search_requests": ws, "web_fetch_requests": wf}}}}) + "\n"

    def test_per_model_accumulation(self):
        self._write(self._line("claude-opus-4-8", inp=100, out=10, ws=1)
                    + self._line("claude-opus-4-8", inp=200, cc=5)
                    + self._line("claude-haiku-4-5", out=50, wf=2))
        detail, off = usage.scan_usage_detailed(self.path, 0)
        self.assertEqual(off, os.path.getsize(self.path))
        m = detail["models"]
        self.assertEqual(m["claude-opus-4-8"], {"in": 300, "out": 10, "cr": 0, "cc": 5, "turns": 2})
        self.assertEqual(m["claude-haiku-4-5"], {"in": 0, "out": 50, "cr": 0, "cc": 0, "turns": 1})
        self.assertEqual(detail["web_search"], 1)
        self.assertEqual(detail["web_fetch"], 2)

    def test_incremental_and_missing_model(self):
        self._write(self._line("claude-opus-4-8", inp=100))
        _, off = usage.scan_usage_detailed(self.path, 0)
        # 无 model 键的行 → "unknown"
        self._write(json.dumps({"message": {"usage": {"input_tokens": 7}}}) + "\n", mode="a")
        detail, _ = usage.scan_usage_detailed(self.path, off)
        self.assertEqual(detail["models"]["unknown"], {"in": 7, "out": 0, "cr": 0, "cc": 0, "turns": 1})

    def test_missing_file(self):
        self.assertEqual(usage.scan_usage_detailed("/no/such.jsonl", 0), ({"models": {}, "web_search": 0, "web_fetch": 0, "last": None}, 0))


class SubagentAndLastTest(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp()

    def _write(self, path, lines):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            for m, inp, cr, cc in lines:
                f.write(json.dumps({"message": {"model": m, "usage": {
                    "input_tokens": inp, "cache_read_input_tokens": cr,
                    "cache_creation_input_tokens": cc}}}) + "\n")

    def test_find_subagent_transcript(self):
        p = os.path.join(self.base, "-data-x", "sid1", "subagents", "agent-aid9.jsonl")
        os.makedirs(os.path.dirname(p))
        open(p, "w").close()
        self.assertEqual(usage.find_subagent_transcript("sid1", "aid9", self.base), p)
        self.assertIsNone(usage.find_subagent_transcript("sid1", "nope", self.base))

    def test_scan_returns_last_model_ctx(self):
        p = os.path.join(self.base, "t.jsonl")
        self._write(p, [("claude-opus-4-8", 100, 200, 0), ("claude-haiku-4-5", 5, 10, 3)])
        detail, off = usage.scan_usage_detailed(p, 0)
        self.assertEqual(detail["last"], {"model": "claude-haiku-4-5", "ctx": 18})  # 5+10+3

    def test_scan_no_usage_last_none(self):
        p = os.path.join(self.base, "e.jsonl")
        with open(p, "w") as f:
            f.write("not json\n")
        detail, _ = usage.scan_usage_detailed(p, 0)
        self.assertIsNone(detail["last"])
