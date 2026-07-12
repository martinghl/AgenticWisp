import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from agenticwisp import cli


class CliDispatchTest(unittest.TestCase):
    def test_unknown_command_returns_1(self):
        self.assertEqual(cli.main(["__nope__"]), 1)

    def test_no_command_returns_1(self):
        self.assertEqual(cli.main([]), 1)

    def test_signal_never_raises_and_returns_0(self):
        import agenticwisp.signal as sig
        orig = sig.main

        def boom(argv):
            raise RuntimeError("boom")

        sig.main = boom
        try:
            self.assertEqual(cli.main(["signal", "Stop"]), 0)
        finally:
            sig.main = orig

    def test_watch_without_textual_returns_1(self):
        orig = cli._have_textual
        cli._have_textual = lambda: False
        try:
            self.assertEqual(cli.main(["watch"]), 1)
        finally:
            cli._have_textual = orig

    def test_demo_without_textual_returns_1(self):
        orig = cli._have_textual
        cli._have_textual = lambda: False
        try:
            self.assertEqual(cli.main(["demo"]), 1)
        finally:
            cli._have_textual = orig

    def test_install_hooks_passes_absolute_base(self):
        import agenticwisp.install_hooks as ih
        captured = {}

        def fake_merge(base, settings_path=None):
            captured["base"] = base
            return [], None, "/x"

        orig = ih.merge_into_settings
        ih.merge_into_settings = fake_merge
        try:
            self.assertEqual(cli.main(["install-hooks", "/abs/bin/wisp"]), 0)
            self.assertEqual(captured["base"], "/abs/bin/wisp")
        finally:
            ih.merge_into_settings = orig

    def test_uninstall_hooks_calls_remove(self):
        import agenticwisp.install_hooks as ih
        called = {}

        def fake_remove(settings_path=None):
            called["yes"] = True
            return ["Stop"], "/b", "/x"

        orig = ih.remove_from_settings
        ih.remove_from_settings = fake_remove
        try:
            self.assertEqual(cli.main(["uninstall-hooks"]), 0)
            self.assertTrue(called.get("yes"))
        finally:
            ih.remove_from_settings = orig


class CliProcessTest(unittest.TestCase):
    def setUp(self):
        self._orig = (cli.RUN_DIR, cli.PIDFILE, cli.LOGFILE)
        self._tmpdirs = []

    def tearDown(self):
        for d in self._tmpdirs:
            shutil.rmtree(d, ignore_errors=True)
        cli.RUN_DIR, cli.PIDFILE, cli.LOGFILE = self._orig

    def _isolate_runtime(self):
        d = tempfile.mkdtemp()
        self._tmpdirs.append(d)
        cli.RUN_DIR = d
        cli.PIDFILE = os.path.join(d, "wispd.pid")
        cli.LOGFILE = os.path.join(d, "wispd.log")
        return d

    def test_up_spawns_wispd_detached(self):
        self._isolate_runtime()
        captured = {}

        class FakeProc:
            pid = 4242

        def fake_popen(argv, **kw):
            captured["argv"] = argv
            captured["kw"] = kw
            return FakeProc()

        orig_popen, orig_running = subprocess.Popen, cli._running
        subprocess.Popen = fake_popen
        cli._running = lambda: None
        try:
            self.assertEqual(cli.main(["up"]), 0)
        finally:
            subprocess.Popen = orig_popen
            cli._running = orig_running
        self.assertEqual(captured["argv"], [sys.executable, "-m", "agenticwisp.wispd"])
        self.assertTrue(captured["kw"].get("start_new_session"))
        with open(cli.PIDFILE) as f:
            self.assertEqual(f.read().strip(), "4242")

    def test_status_reports_not_running(self):
        self._isolate_runtime()
        orig = cli._running
        cli._running = lambda: None
        try:
            self.assertEqual(cli.main(["status"]), 0)
        finally:
            cli._running = orig

    def test_down_removes_pidfile(self):
        d = self._isolate_runtime()
        with open(cli.PIDFILE, "w") as f:
            f.write("999999")  # almost-certainly-dead pid
        self.assertEqual(cli.main(["down"]), 0)
        self.assertFalse(os.path.exists(cli.PIDFILE))
