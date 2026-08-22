"""The fzf hint has to name a command that works on the machine reading it.

The person most likely to see this is on Linux without fzf, where the previous
hardcoded `brew install fzf` was simply wrong, and "see the fzf homepage" meant
going to read a page instead of running a line.
"""

import unittest
from unittest import mock

from load_agsearch import load_agsearch


class FzfHintTests(unittest.TestCase):
    def setUp(self):
        self.ag = load_agsearch()

    def _hint(self, present):
        with mock.patch.object(self.ag.shutil, "which",
                               side_effect=lambda t: t if t in present else None):
            return self.ag.fzf_install_hint()

    def test_names_the_package_manager_that_exists(self):
        for tools, expected in (
            ({"brew"}, "brew install fzf"),
            ({"apt-get"}, "sudo apt install fzf"),
            ({"dnf"}, "sudo dnf install fzf"),
            ({"pacman"}, "sudo pacman -S fzf"),
            ({"zypper"}, "sudo zypper install fzf"),
            ({"apk"}, "sudo apk add fzf"),
        ):
            with self.subTest(tools=tools):
                self.assertEqual(self._hint(tools), expected)

    def test_does_not_suggest_brew_on_a_linux_box(self):
        """The original bug: brew named on a machine that has never had it."""
        self.assertNotIn("brew", self._hint({"apt-get"}))

    def test_falls_back_to_the_homepage_when_nothing_is_recognised(self):
        self.assertIn("github.com/junegunn/fzf", self._hint(set()))

    def test_prefers_brew_when_both_exist(self):
        """Linuxbrew alongside apt: brew installs without sudo, so prefer it."""
        self.assertEqual(self._hint({"brew", "apt-get"}), "brew install fzf")


if __name__ == "__main__":
    unittest.main()
