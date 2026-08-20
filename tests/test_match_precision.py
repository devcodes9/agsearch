"""Prefix matching exists to undo stemming, so it should only apply where stemming happened.

Applying it everywhere means `pr` matches `print`, `previously`, `prisma`, which is most of a
transcript. The word you typed unchanged is the word you meant.
"""

import unittest

from load_agsearch import load_agsearch


class WholeWordTests(unittest.TestCase):
    def test_an_unstemmed_key_does_not_match_a_longer_word(self):
        ag = load_agsearch()
        self.assertFalse(ag._at_word_start("i will print the env", "pr", whole=True))
        self.assertTrue(ag._at_word_start("i will print the env", "pr"))

    def test_an_unstemmed_key_still_matches_itself(self):
        ag = load_agsearch()
        self.assertTrue(ag._at_word_start("the pr is green", "pr", whole=True))
        self.assertTrue(ag._at_word_start("ends with pr", "pr", whole=True))

    def test_a_stem_keeps_reaching_its_inflections(self):
        ag = load_agsearch()
        for text in ("the migration plan", "we are migrating", "please migrate"):
            with self.subTest(text=text):
                self.assertTrue(ag._at_word_start(text, "migrat"))


class FuzzyTierTests(unittest.TestCase):
    def test_short_terms_are_not_treated_as_typos(self):
        """`p...r` inside six characters matches almost any English text."""
        ag = load_agsearch()
        chatter = "i will print the environment and compare the two step by step " * 20
        rows = [[f"sid{i}", "/r", "2026-08-19", "cc", "cli", f"Session {i}", "hello", chatter]
                for i in range(6)]
        ranked = ag.rank_sessions(rows, ag.parse_query("pr"), usage={}, now=0)
        self.assertEqual(ranked, [], "no session is about PRs")

    def test_a_real_typo_still_resolves(self):
        ag = load_agsearch()
        rows = [["sid_noise", "/r", "2026-08-19", "cc", "cli", "Unrelated", "hello", "nothing here"],
                ["sid_target", "/r", "2026-08-19", "cc", "cli", "Debug webcache flag",
                 "investigate webcache flag", "webcache flag rollout issue in production"]]
        ranked = ag.rank_sessions(rows, ag.parse_query("webcahe flag"), usage={}, now=0)
        self.assertEqual(ranked[0][2][ag.C_SID], "sid_target")
        self.assertEqual(ranked[0][1], 2)


if __name__ == "__main__":
    unittest.main()
