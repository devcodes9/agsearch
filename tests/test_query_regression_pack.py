import unittest

from load_agsearch import load_agsearch


def _fixture_rows():
    # sessions.tsv row schema:
    # sid, cwd, date, source, kind, title, first prompt, blob
    return [
        [
            "sid_head_exact",
            "/repo/payments",
            "2026-08-19",
            "cc",
            "cli",
            "Stripe webhook retry fix",
            "Investigate Stripe webhook retries",
            "stripe webhook retries with signature errors",
        ],
        [
            "sid_head_noise",
            "/repo/payments",
            "2026-08-19",
            "cc",
            "cli",
            "Webhook notes",
            "General notes",
            "webhook notes and docs",
        ],
        [
            "sid_torso_stem",
            "/repo/law",
            "2026-08-19",
            "cc",
            "cli",
            "EU legislate updates",
            "Plan EU legislation rollout",
            "we should legislate new regional requirements",
        ],
        [
            "sid_migration",
            "/repo/data",
            "2026-08-19",
            "cc",
            "cli",
            "Migration checklist",
            "How to migrate safely",
            "migration checklist and migration rollback steps",
        ],
        [
            "sid_typo_target",
            "/repo/ops",
            "2026-08-19",
            "cc",
            "cli",
            "Debug webcache flag production issue",
            "Investigate webcache flag",
            "webcache flag rollout issue in production",
        ],
        [
            "sid_typo_noise",
            "/repo/ops",
            "2026-08-19",
            "cc",
            "cli",
            "Debug cache flag issue",
            "Investigate cache flag",
            "cache flag rollout issue in production",
        ],
        [
            "sid_first_prompt",
            "/repo/app",
            "2026-08-19",
            "cc",
            "cli",
            "DB move",
            "Please migrate the billing database this week",
            "unrelated chatter about dashboards",
        ],
        [
            "sid_repeated_lines",
            "/repo/app",
            "2026-08-19",
            "cc",
            "cli",
            "Notes",
            "Daily standup notes",
            ("please migrate the logs. " * 80),
        ],
    ]


class QueryRegressionPackTests(unittest.TestCase):
    def test_head_torso_tail_queries_rank_expected_sessions_first(self):
        ag = load_agsearch()
        rows = _fixture_rows()
        cases = [
            ("stripe webhook", "sid_head_exact"),
            ("eu legislation", "sid_torso_stem"),
            ("webcahe flag", "sid_typo_target"),
        ]
        for query, want_sid in cases:
            with self.subTest(query=query):
                ranked = ag.rank_sessions(rows, ag.parse_query(query), usage={}, now=0)
                self.assertGreater(len(ranked), 0)
                self.assertEqual(ranked[0][2][ag.C_SID], want_sid)

    def test_tail_typo_query_matches_both_concepts(self):
        ag = load_agsearch()
        rows = _fixture_rows()
        ranked = ag.rank_sessions(rows, ag.parse_query("webcahe flag"), usage={}, now=0)
        self.assertEqual(ranked[0][2][ag.C_SID], "sid_typo_target")
        self.assertEqual(ranked[0][1], 2)  # typo-resolved "webcahe" + exact "flag"

    def test_stopword_heavy_query_reduces_to_signal_term(self):
        ag = load_agsearch()
        rows = _fixture_rows()
        qterms = ag.parse_query("how migration")
        self.assertEqual([w for w, _s in qterms], ["migration"])
        ranked = ag.rank_sessions(rows, qterms, usage={}, now=0)
        self.assertEqual(ranked[0][2][ag.C_SID], "sid_migration")

    def test_unseen_query_returns_no_matches(self):
        ag = load_agsearch()
        rows = _fixture_rows()
        ranked = ag.rank_sessions(rows, ag.parse_query("quantum unicorn"), usage={}, now=0)
        self.assertEqual(ranked, [])

    def test_first_prompt_beats_repeated_body_line_hits(self):
        ag = load_agsearch()
        rows = _fixture_rows()
        ranked = ag.rank_sessions(rows, ag.parse_query("migrate billing"), usage={}, now=0)
        top = [r[2][ag.C_SID] for r in ranked[:2]]
        self.assertEqual(ranked[0][2][ag.C_SID], "sid_first_prompt", top)


if __name__ == "__main__":
    unittest.main()
