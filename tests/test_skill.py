"""The skill is documentation an agent executes, so a stale line in it is a bug.

It ships as a Claude Code plugin: the marketplace manifest points at this repo, and the
skill sits where Claude Code expects to find it. These tests pin the manifests to the file
they promise, and pin the skill to the CLI it teaches.
"""

import json
import pathlib
import re
import unittest

from load_agsearch import load_agsearch

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "agsearch" / "SKILL.md"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    out = {}
    for line in (m.group(1).splitlines() if m else []):
        if ": " in line:
            k, v = line.split(": ", 1)
            out[k.strip()] = v.strip()
    return out


class SkillTests(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text()
        self.script = (ROOT / "agsearch").read_text()

    def test_frontmatter_names_the_skill(self):
        self.assertEqual(frontmatter(self.text).get("name"), "agsearch")

    def test_the_description_says_when_to_fire(self):
        """The description is the only part always in context. It has to carry the triggers."""
        desc = frontmatter(self.text).get("description", "")
        self.assertIn("session", desc.lower())
        self.assertGreater(len(desc), 80, desc)

    def test_every_flag_the_skill_teaches_exists_in_the_cli(self):
        """A skill naming a removed flag sends the agent to a dead command."""
        for flag in sorted(set(re.findall(r"agsearch [^\n]*?(--[a-z][a-z-]+)", self.text))):
            self.assertIn(f'"{flag}"', self.script,
                          f"the skill teaches {flag}, the CLI has no such flag")

    def test_every_subcommand_the_skill_teaches_exists(self):
        for sub in sorted(set(re.findall(r"agsearch (read|-n) ", self.text))):
            self.assertIn(f'"{sub}"', self.script)


class PluginManifestTests(unittest.TestCase):
    """`/plugin install` fails silently-ish on a manifest that points at nothing."""

    def test_the_marketplace_lists_this_plugin(self):
        m = json.loads(MARKETPLACE.read_text())
        names = [p["name"] for p in m["plugins"]]
        self.assertIn(json.loads(PLUGIN.read_text())["name"], names)

    def test_every_plugin_source_exists(self):
        for p in json.loads(MARKETPLACE.read_text())["plugins"]:
            self.assertTrue((ROOT / p["source"]).is_dir(), p["source"])

    def test_the_source_actually_contains_the_skill(self):
        for p in json.loads(MARKETPLACE.read_text())["plugins"]:
            found = list((ROOT / p["source"]).glob("skills/*/SKILL.md"))
            self.assertTrue(found, f"{p['source']} has no skills/*/SKILL.md")

    def test_the_plugin_version_is_a_version(self):
        """Users only get updates when this changes, so a missing one freezes them."""
        self.assertRegex(json.loads(PLUGIN.read_text())["version"], r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
