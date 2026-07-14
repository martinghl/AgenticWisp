import os
import unittest

try:
    import tomllib
except ImportError:  # py < 3.11
    tomllib = None


class VersionTest(unittest.TestCase):
    def test_version_is_012(self):
        import agenticwisp
        self.assertEqual(agenticwisp.__version__, "0.1.2")

    def test_docstring_dropped_old_remote_framing(self):
        import agenticwisp
        self.assertNotIn("跨越大陆", agenticwisp.__doc__ or "")

    @unittest.skipUnless(tomllib, "needs tomllib (py3.11+)")
    def test_pyproject_entrypoint_and_dynamic_version(self):
        root = os.path.dirname(os.path.dirname(__file__))
        with open(os.path.join(root, "pyproject.toml"), "rb") as f:
            data = tomllib.load(f)
        self.assertEqual(data["project"]["scripts"]["wisp"], "agenticwisp.cli:main")
        self.assertIn("version", data["project"]["dynamic"])
        self.assertNotIn("version", data["project"])  # not both static + dynamic
