"""The version literal is the anchor every packaging channel reads.

Homebrew, PyPI and the installer all need to agree on one string. These tests
pin the two properties that keep them from drifting: the literal is a real
release version, and it can be read out of the file by a regex without
importing agsearch (which is how build backends and shell scripts read it).
"""

import pathlib
import re
import subprocess
import sys
import unittest

from load_agsearch import load_agsearch

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "agsearch"

# Same pattern packaging is expected to use. Keep in sync with pyproject/formula.
VERSION_RE = re.compile(r'^__version__ = "([^"]+)"$', re.M)


class VersionTests(unittest.TestCase):
    def setUp(self):
        self.ag = load_agsearch()

    def test_version_is_a_release_version(self):
        self.assertRegex(self.ag.__version__, r"^\d+\.\d+\.\d+([-.][0-9A-Za-z.]+)?$")

    def test_version_is_readable_without_importing(self):
        """Packaging reads the literal with a regex — it must stay greppable."""
        found = VERSION_RE.findall(SCRIPT.read_text())
        self.assertEqual(len(found), 1, "expected exactly one __version__ literal")
        self.assertEqual(found[0], self.ag.__version__)

    def test_version_flag_prints_it_and_exits_clean(self):
        for flag in ("--version", "-V"):
            with self.subTest(flag=flag):
                out = subprocess.run(
                    [sys.executable, str(SCRIPT), flag],
                    capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(out.returncode, 0, out.stderr)
                self.assertEqual(out.stdout.strip(), "agsearch " + self.ag.__version__)

    def test_version_flag_does_not_build_the_index(self):
        """--version must answer before any cache work, so it is safe in a
        Homebrew sandbox and in `agsearch --version` health checks."""
        src = SCRIPT.read_text()
        version_at = src.index('elif a in ("-V", "--version")')
        build_at = src.index("lines = build_index(")
        self.assertLess(version_at, build_at)


if __name__ == "__main__":
    unittest.main()
