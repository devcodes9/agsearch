"""Packaging metadata must not drift from the CLI.

PyPI uploads are irreversible — a file published under the wrong version can
be yanked but never replaced — so the cheapest place to catch a mismatch is
here, on every PR.
"""

import pathlib
import re
import unittest

from load_agsearch import load_agsearch

ROOT = pathlib.Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"


def _field(name):
    """Read a top-level `name = "value"` out of pyproject without tomllib,
    which is 3.11+ and this project supports 3.9."""
    m = re.search(rf'^{name} = "([^"]+)"$', PYPROJECT.read_text(), re.M)
    return m.group(1) if m else None


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.ag = load_agsearch()
        self.text = PYPROJECT.read_text()

    def test_version_is_derived_not_duplicated(self):
        """The version must be read from the source literal, not restated —
        a second copy is a second thing to forget to bump."""
        self.assertIn('dynamic = ["version"]', self.text)
        self.assertNotRegex(self.text, r'^version = "')

    def test_hatch_version_pattern_matches_the_literal(self):
        """The regex in pyproject has to actually find __version__ in agsearch."""
        m = re.search(r"^pattern = '([^']+)'$", self.text, re.M)
        self.assertIsNotNone(m, "no [tool.hatch.version] pattern found")
        found = re.search(m.group(1), (ROOT / "agsearch").read_text(), re.M)
        self.assertIsNotNone(found, "hatch pattern does not match agsearch")
        self.assertEqual(found.group("version"), self.ag.__version__)

    def test_entry_point_target_exists_and_takes_no_arguments(self):
        """[project.scripts] calls the target with zero arguments; main(argv)
        would raise TypeError on every `uvx agsearch` invocation."""
        self.assertIn('agsearch = "agsearch:_entry"', self.text)
        self.assertTrue(callable(self.ag._entry))

        import inspect
        required = [
            p for p in inspect.signature(self.ag._entry).parameters.values()
            if p.default is inspect.Parameter.empty
            and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
        ]
        self.assertEqual(required, [])

    def test_stays_dependency_free(self):
        """Zero dependencies is what makes `uvx agsearch` resolve instantly.
        Adding one is a real decision, so make it a failing test first."""
        self.assertIn("dependencies = []", self.text)

    def test_declares_the_supported_interpreter_floor(self):
        self.assertEqual(_field("requires-python"), ">=3.9")

    def test_the_extensionless_script_is_mapped_to_an_importable_module(self):
        """agsearch ships extensionless (that is what curl | sh puts on PATH),
        so the wheel has to force-include it as agsearch.py or the console
        script cannot import it."""
        self.assertIn('force-include = { "agsearch" = "agsearch.py" }', self.text)


if __name__ == "__main__":
    unittest.main()
