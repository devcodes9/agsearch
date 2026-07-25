#!/usr/bin/env python3
"""Ranking tests for agsearch, over a small fixture corpus.

Run with:  python3 -m unittest discover -s tests -v     (or: python3 tests/test_ranking.py)

The corpus is deliberately tiny and hand-written so every expected ordering can be justified
from the fixture text itself, not from whatever happens to be in ~/.claude today.
"""

import os
import sys
import time
import shutil
import tempfile
import unittest
import importlib.util
import importlib.machinery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_loader = importlib.machinery.SourceFileLoader("agsearch", os.path.join(REPO, "agsearch"))
_spec = importlib.util.spec_from_loader("agsearch", _loader)
ag = importlib.util.module_from_spec(_spec)
_loader.exec_module(ag)


NOW = time.mktime(time.strptime("2026-07-25", "%Y-%m-%d"))


def row(sid, title, first, blob, date="2026-07-01", cwd="/w/proj", kind="cli", source="cc"):
    """One sessions.tsv row as cmd_filter would split it."""
    return [sid, cwd, date, source, kind, title, first, blob]


def sids(scored):
    return [f[ag.C_SID] for _score, _m, f in scored]


def rank(rows, query, usage=None, now=NOW):
    return ag.rank_sessions(rows, ag.parse_query(query), usage=usage, now=now)


# A long, rambling session that mentions lots of things once — the kind that used to swamp
# the list purely by being big.
LONG_BLOB = (" · ".join([
    "we talked about deployment and caching and the stripe webhook signature at some point",
    "then about postgres indexes, then about the ci pipeline, then about flaky tests",
] + ["assorted follow-up discussion about unrelated refactoring work"] * 200))


class TestFieldWeighting(unittest.TestCase):
    def test_first_prompt_phrase_ranks_top1(self):
        """AC: a distinctive phrase from a session's first prompt puts that session at #1."""
        rows = [
            row("body-mention", "Deploy notes", "help me deploy the api",
                "sure · by the way the quarterly tax reconciliation came up once here · ok"),
            row("first-prompt", "Untitled", "fix the quarterly tax reconciliation job",
                "looked at the job · patched it · tests pass"),
            row("noise", "CI pipeline", "make ci faster", LONG_BLOB),
        ]
        self.assertEqual(sids(rank(rows, "quarterly tax reconciliation"))[0], "first-prompt")

    def test_title_still_counts(self):
        rows = [
            row("titled", "Stripe webhook signature", "hey", "some chat"),
            row("passing", "Random", "hey", "we mentioned stripe once"),
        ]
        self.assertEqual(sids(rank(rows, "stripe"))[0], "titled")


class TestLengthNormalization(unittest.TestCase):
    def test_short_exact_match_beats_long_unrelated_session(self):
        """AC: a very long session that merely mentions the term no longer wins."""
        rows = [
            row("long", "Misc engineering chat", "lots of things", LONG_BLOB),
            row("short", "Stripe webhook", "debug the stripe webhook signature mismatch",
                "the stripe webhook signature was wrong · fixed the secret"),
        ]
        self.assertEqual(sids(rank(rows, "stripe webhook signature"))[0], "short")

    def test_length_norm_penalises_padding(self):
        """Same hits, same fields — the padded transcript must not score higher."""
        core = "we fixed the stripe webhook signature"
        rows = [
            row("tight", "t", "q", core),
            row("padded", "t", "q", core + (" · unrelated chatter" * 500)),
        ]
        scored = {f[ag.C_SID]: s for s, _m, f in rank(rows, "stripe webhook signature")}
        self.assertGreater(scored["tight"], scored["padded"])


class TestBoosts(unittest.TestCase):
    def test_recency_breaks_ties(self):
        rows = [
            row("old", "Stripe webhook", "stripe webhook", "stripe webhook", date="2024-01-01"),
            row("new", "Stripe webhook", "stripe webhook", "stripe webhook", date="2026-07-24"),
        ]
        self.assertEqual(sids(rank(rows, "stripe webhook")), ["new", "old"])

    def test_usage_breaks_ties(self):
        rows = [
            row("never", "Stripe webhook", "stripe webhook", "stripe webhook"),
            row("often", "Stripe webhook", "stripe webhook", "stripe webhook"),
        ]
        self.assertEqual(sids(rank(rows, "stripe webhook", usage={"often": 5})),
                         ["often", "never"])

    def test_boosts_cannot_float_a_weak_match_over_a_strong_one(self):
        """Bounded on purpose: relevance still dominates recency + usage combined."""
        rows = [
            row("weak", "Misc", "hello", "stripe came up once", date="2026-07-25"),
            row("strong", "Stripe webhook signature", "debug the stripe webhook signature",
                "stripe webhook signature stripe webhook signature", date="2023-01-01"),
        ]
        self.assertEqual(sids(rank(rows, "stripe webhook signature", usage={"weak": 50}))[0],
                         "strong")

    def test_boost_bounds(self):
        f_now = row("a", "t", "q", "b", date="2026-07-25")
        f_old = row("b", "t", "q", "b", date="2000-01-01")
        self.assertAlmostEqual(ag._boost(f_now, {}, NOW), 1.0 + ag.RECENCY_W, places=6)
        self.assertAlmostEqual(ag._boost(f_old, {}, NOW), 1.0, places=3)
        self.assertLessEqual(ag._boost(f_now, {"a": 10_000}, NOW),
                             1.0 + ag.RECENCY_W + ag.USAGE_W + 1e-9)

    def test_undated_row_is_not_boosted(self):
        self.assertAlmostEqual(ag._boost(row("x", "t", "q", "b", date=""), {}, NOW), 1.0, places=3)


class TestRankingInvariants(unittest.TestCase):
    def test_coverage_outranks_relevance(self):
        """Matching both words still beats a heavy match on one — unchanged behaviour."""
        rows = [
            row("both", "x", "stripe webhook", "stripe webhook"),
            row("one", "x", "stripe stripe stripe", "stripe " * 50),
        ]
        self.assertEqual(sids(rank(rows, "stripe webhook"))[0], "both")

    def test_auto_sessions_are_demoted_not_hidden(self):
        rows = [
            row("auto1", "Stripe webhook signature", "stripe webhook signature",
                "stripe webhook signature", kind="auto"),
            row("mine", "Misc", "hello", "stripe once", kind="cli"),
        ]
        self.assertEqual(sids(rank(rows, "stripe")), ["mine", "auto1"])

    def test_non_matching_sessions_are_dropped(self):
        rows = [row("a", "x", "y", "nothing relevant here whatsoever")]
        self.assertEqual(rank(rows, "stripe webhook"), [])

    def test_typo_falls_back_to_subsequence(self):
        rows = [row("lib", "alibrary migration", "port alibrary", "alibrary alibrary")]
        self.assertEqual(sids(rank(rows, "alibrry")), ["lib"])

    def test_stemming_still_matches(self):
        rows = [row("m", "Database migration", "run the migration", "migrating the database")]
        self.assertTrue(sids(rank(rows, "migrate")))


class TestUsageCounts(unittest.TestCase):
    def test_parses_resume_log(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        log = os.path.join(d, "last-resume.log")
        with open(log, "w") as fh:
            fh.write("cd /a && claude --resume 1a228037-e822-442b-a76b-cc6f6fd2a658   [x]\n")
            fh.write("cd /a && claude --resume 1a228037-e822-442b-a76b-cc6f6fd2a658   [x]\n")
            fh.write("cd /b && codex resume f0f3fd75-df9f-46b2-8764-035990e15f56   [x]\n")
            fh.write("garbage line with no session\n")
        self.assertEqual(ag._usage_counts(log), {
            "1a228037-e822-442b-a76b-cc6f6fd2a658": 2,
            "f0f3fd75-df9f-46b2-8764-035990e15f56": 1,
        })

    def test_missing_log_is_not_an_error(self):
        self.assertEqual(ag._usage_counts("/nonexistent/last-resume.log"), {})


class TestColumnLayoutRoundTrip(unittest.TestCase):
    """build_sessions writes what cmd_filter reads — catches a column drift at either end."""

    def test_build_then_filter(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        old = (ag.SESSIONS_PATH, ag.INDEX_PATH, ag.SUBMAP_PATH)
        ag.SESSIONS_PATH = os.path.join(d, "sessions.tsv")
        ag.INDEX_PATH = os.path.join(d, "index.json")
        ag.SUBMAP_PATH = os.path.join(d, "submap.json")
        self.addCleanup(lambda: setattr_all(ag, old))

        S = ag.SEP
        index_lines = [
            S.join(["sid-a", "/w/a", "b", "2026-07-20T10:00:00Z", "user", "0", "Tax job",
                    "fix the quarterly tax reconciliation job", "cli"]),
            S.join(["sid-b", "/w/b", "b", "2026-07-21T10:00:00Z", "user", "0", "CI",
                    "make ci faster", "cli"]),
        ]
        ag.build_sessions(index_lines)

        with open(ag.SESSIONS_PATH) as fh:
            written = fh.read().splitlines()
        self.assertTrue(all(len(l.split(S)) == ag.SESSION_COLS for l in written))

        rows = [l.split(S) for l in written]
        by_sid = {f[ag.C_SID]: f for f in rows}
        self.assertEqual(by_sid["sid-a"][ag.C_FIRST], "fix the quarterly tax reconciliation job")
        self.assertEqual(sids(rank(rows, "quarterly tax reconciliation"))[0], "sid-a")


def setattr_all(mod, old):
    mod.SESSIONS_PATH, mod.INDEX_PATH, mod.SUBMAP_PATH = old


if __name__ == "__main__":
    unittest.main(verbosity=2)
