import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


class BinWispTest(unittest.TestCase):
    def _wisp(self):
        return os.path.realpath(
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "bin", "wisp"))

    def test_unknown_command_prints_new_cli_usage_and_exits_1(self):
        env = dict(os.environ, WISP_PYTHON=sys.executable)
        r = subprocess.run([self._wisp(), "__nope__"], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 1)
        out = (r.stdout + r.stderr).lower()
        self.assertIn("usage", out)
        self.assertIn("demo", out)             # only the new cli usage lists these
        self.assertIn("uninstall-hooks", out)

    def test_install_hooks_writes_absolute_launcher_path(self):
        home = tempfile.mkdtemp()
        try:
            env = dict(os.environ, WISP_PYTHON=sys.executable, HOME=home)
            r = subprocess.run([self._wisp(), "install-hooks"],
                               capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            settings = os.path.join(home, ".claude", "settings.json")
            with open(settings) as f:
                data = json.load(f)
            # gather every hook command string in the file
            cmds = []
            for groups in data.get("hooks", {}).values():
                for g in groups:
                    for h in g.get("hooks", []):
                        cmds.append(h.get("command", ""))
            self.assertTrue(cmds, "no hook commands written")
            # every wisp hook command must invoke the ABSOLUTE bin/wisp path + 'signal <Event>'
            wisp_abs = self._wisp()
            wisp_cmds = [c for c in cmds if " signal " in c]
            self.assertTrue(wisp_cmds)
            for c in wisp_cmds:
                self.assertTrue(c.startswith(wisp_abs + " signal "),
                                "hook command not absolute-launcher-based: %r" % c)
        finally:
            shutil.rmtree(home, ignore_errors=True)

    def test_signal_exits_0_when_hub_unreachable(self):
        # `signal` with a bad port is a no-op that still exits 0, proving the shim reached cli.
        env = dict(os.environ, WISP_PYTHON=sys.executable, WISP_PORT="1")
        r = subprocess.run([self._wisp(), "signal", "Stop"], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
