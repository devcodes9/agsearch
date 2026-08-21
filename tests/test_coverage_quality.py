"""Coverage counts words the session really contains, not words we guessed at.

The typo tier resolves a term by subsequence match, which any long enough text can satisfy.
Letting that count toward coverage meant a session containing `b i l l i n g` spread across a
sentence outranked one genuinely about billing at three times the relevance score, because
coverage is sorted above score.
"""

import unittest

from load_agsearch import load_agsearch


class CoverageQualityTests(unittest.TestCase):
    def _rows(self):
        return [
            ["sid_real", "/repo", "2026-08-19", "cc", "cli", "Billing work", "fix billing",
             "the billing retry path needs a fix today " * 6],
            ["sid_subsequence", "/repo", "2026-08-19", "cc", "cli", "Notes", "misc",
             "b i l l i n g dashboards were discussed and the migration plan was reviewed " * 6],
        ]

    def test_a_real_partial_match_outranks_a_wider_guess(self):
        ag = load_agsearch()
        ranked = ag.rank_sessions(self._rows(), ag.parse_query("billing migration"),
                                  usage={}, now=0)
        self.assertEqual(ranked[0][2][ag.C_SID], "sid_real")

    def test_the_badge_still_reports_the_resolved_concept(self):
        """Ranking ignores the guess; the count shown to the user does not hide it."""
        ag = load_agsearch()
        ranked = ag.rank_sessions(self._rows(), ag.parse_query("billing migration"),
                                  usage={}, now=0)
        by_sid = {r[2][ag.C_SID]: r[1] for r in ranked}
        self.assertEqual(by_sid["sid_real"], 1)
        self.assertEqual(by_sid["sid_subsequence"], 2)

    def test_a_typo_still_resolves_to_the_session_that_means_it(self):
        ag = load_agsearch()
        rows = [
            ["sid_noise", "/repo", "2026-08-19", "cc", "cli", "Unrelated", "hi", "nothing here"],
            ["sid_target", "/repo", "2026-08-19", "cc", "cli", "Debug webcache flag",
             "investigate webcache flag", "webcache flag rollout issue in production"],
        ]
        ranked = ag.rank_sessions(rows, ag.parse_query("webcahe flag"), usage={}, now=0)
        self.assertEqual(ranked[0][2][ag.C_SID], "sid_target")
        self.assertEqual(ranked[0][1], 2)

    def test_real_coverage_still_beats_relevance(self):
        """Two words really present must outrank one word present with a bigger score."""
        ag = load_agsearch()
        rows = [
            ["sid_one_word", "/repo", "2026-08-19", "cc", "cli", "Stripe", "stripe",
             "stripe stripe stripe stripe stripe " * 20],
            ["sid_both_words", "/repo", "2026-08-19", "cc", "cli", "Notes", "notes",
             "stripe webhook signature check"],
        ]
        ranked = ag.rank_sessions(rows, ag.parse_query("stripe webhook"), usage={}, now=0)
        self.assertEqual(ranked[0][2][ag.C_SID], "sid_both_words")

    def test_rank_sessions_still_returns_score_matched_row(self):
        ag = load_agsearch()
        ranked = ag.rank_sessions(self._rows(), ag.parse_query("billing"), usage={}, now=0)
        self.assertEqual(len(ranked[0]), 3)


if __name__ == "__main__":
    unittest.main()
