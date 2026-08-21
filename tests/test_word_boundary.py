"""Short query terms must not match inside longer words.

`pr` is a substring of 700 of 718 local sessions but a word in only 182, because it hides in
`approach`, `improve`, `compress`. Counting those as hits collapses the term's idf and makes
the coverage tiebreaker meaningless, so the term the query was actually about loses.
"""

import unittest

from load_agsearch import load_agsearch


class WordStartTests(unittest.TestCase):
    def test_does_not_match_inside_a_longer_word(self):
        ag = load_agsearch()
        self.assertFalse(ag._at_word_start("approach improve compress", "pr"))

    def test_matches_a_standalone_word(self):
        ag = load_agsearch()
        self.assertTrue(ag._at_word_start("the pr is ready", "pr"))
        self.assertTrue(ag._at_word_start("pr opened", "pr"))

    def test_keeps_prefix_semantics_so_stems_still_match_inflections(self):
        ag = load_agsearch()
        for text in ("we are migrating", "the migration plan", "please migrate it"):
            with self.subTest(text=text):
                self.assertTrue(ag._at_word_start(text, "migrat"))

    def test_punctuation_and_slashes_start_a_word(self):
        ag = load_agsearch()
        self.assertTrue(ag._at_word_start("see github.com/org/repo/pull/1144", "1144"))
        self.assertTrue(ag._at_word_start("(pr) landed", "pr"))

    def test_underscore_does_not_start_a_word(self):
        ag = load_agsearch()
        self.assertFalse(ag._at_word_start("some_pr_helper", "pr"))


class RankingConsequenceTests(unittest.TestCase):
    def _rows(self):
        """Enough real `pr` sessions that the term is not rare.

        rank_sessions treats a term appearing in <= 2 sessions as a probable typo and falls
        back to subsequence matching, which any long text satisfies. On a two-row fixture that
        fires for every term and hides what is being tested.
        """
        rows = [[f"sid_real_{i}", "/repo/a", "2026-08-19", "cc", "cli",
                 "Ship it", "open the pr", f"the pr is ready for review number {i}"]
                for i in range(4)]
        rows.append(["sid_inside_words", "/repo/b", "2026-08-19", "cc", "cli",
                     "Notes", "general notes", "approach improve compress reprocess " * 40])
        return rows

    def test_a_session_that_only_hides_the_term_inside_words_does_not_match(self):
        ag = load_agsearch()
        ranked = ag.rank_sessions(self._rows(), ag.parse_query("pr"), usage={}, now=0)
        sids = [r[2][ag.C_SID] for r in ranked]
        self.assertNotIn("sid_inside_words", sids)
        self.assertEqual(len(sids), 4)

    def test_preview_counts_agree_with_what_the_ranker_matched(self):
        """The invariant from the preview-alignment cut: same keys, same matching rule."""
        ag = load_agsearch()
        body = "approach improve compress"
        keys = ag.query_keys(ag.parse_query("pr"))
        self.assertFalse(all(ag._at_word_start(body, k) for k in keys))


if __name__ == "__main__":
    unittest.main()
