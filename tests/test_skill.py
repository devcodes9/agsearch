"""The skill is documentation an agent executes, so a stale line is a bug, not a typo.

Two copies exist by necessity: the file people read in the repo, and the literal inside the
script, which is the only copy brew, uv and the curl installer carry. These tests pin them
together, and pin the skill to the CLI it describes.
"""

import io
import os
import pathlib
import re
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

from load_agsearch import load_agsearch

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "agsearch" / "SKILL.md"


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ": " in line:
            k, v = line.split(": ", 1)
            out[k.strip()] = v.strip()
    return out


class SkillFileTests(unittest.TestCase):
    def setUp(self):
        self.ag = load_agsearch()
        self.text = SKILL.read_text()

    def test_the_shipped_copy_matches_the_repo_copy(self):
        """Anyone who installed by brew, uv or curl gets the literal, never the repo file."""
        self.assertEqual(self.ag.SKILL_MD, self.text,
                         "SKILL.md and SKILL_MD have drifted. Run: python3 tools/sync-skill.py")

    def test_frontmatter_names_the_skill(self):
        self.assertEqual(frontmatter(self.text).get("name"), "agsearch")

    def test_the_description_says_when_to_fire(self):
        """The description is the only part always in context. It has to carry the triggers."""
        desc = frontmatter(self.text).get("description", "")
        self.assertIn("session", desc.lower())
        self.assertGreater(len(desc), 80, desc)

    def test_every_flag_the_skill_teaches_exists_in_the_cli(self):
        """A skill that names a removed flag sends the agent to a dead command."""
        script = (ROOT / "agsearch").read_text()
        for flag in sorted(set(re.findall(r"agsearch [^\n]*?(--[a-z][a-z-]+)", self.text))):
            self.assertIn(f'"{flag}"', script, f"the skill teaches {flag}, the CLI has no such flag")

    def test_every_subcommand_the_skill_teaches_exists(self):
        for sub in sorted(set(re.findall(r"agsearch (read|-n) ", self.text))):
            self.assertIn(f'"{sub}"', (ROOT / "agsearch").read_text())


class InstallSkillTests(unittest.TestCase):
    def setUp(self):
        self.ag = load_agsearch()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ag.SKILL_DIR = os.path.join(self.tmp.name, ".claude", "skills", "agsearch")
        self.path = os.path.join(self.ag.SKILL_DIR, "SKILL.md")

    def install(self, force=False):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = self.ag.install_skill(force=force)
        return code, out.getvalue() + err.getvalue()

    def test_it_writes_the_skill_where_claude_code_looks(self):
        code, _out = self.install()
        self.assertEqual(code, 0)
        self.assertEqual(open(self.path).read(), self.ag.SKILL_MD)

    def test_running_it_twice_changes_nothing(self):
        self.install()
        code, out = self.install()
        self.assertEqual(code, 0)
        self.assertIn("already installed", out)

    def test_an_edited_skill_survives(self):
        """People tune skills. Reverting someone's edit on an upgrade is worse than stale."""
        self.install()
        open(self.path, "w").write("mine\n")
        code, out = self.install()
        self.assertEqual(code, 1)
        self.assertEqual(open(self.path).read(), "mine\n")
        self.assertIn("--force", out)

    def test_force_replaces_an_edited_skill(self):
        self.install()
        open(self.path, "w").write("mine\n")
        code, _out = self.install(force=True)
        self.assertEqual(code, 0)
        self.assertEqual(open(self.path).read(), self.ag.SKILL_MD)


if __name__ == "__main__":
    unittest.main()
