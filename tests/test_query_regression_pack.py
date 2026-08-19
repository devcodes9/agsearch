import importlib.machinery
import importlib.util
import pathlib
import unittest


def _load_agsearch():
    root = pathlib.Path(__file__).resolve().parents[1]
    path = root / "agsearch"
    loader = importlib.machinery.SourceFileLoader("agsearch_under_test", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


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
            "Debug alibrary flag production issue",
            "Investigate alibrary flag",
            "alibrary flag rollout issue in production",
        ],
        [
            "sid_typo_noise",
            "/repo/ops",
            "2026-08-19",
            "cc",
            "cli",
            "Debug library flag issue",
            "Investigate library flag",
            "library flag rollout issue in production",
        ],
    ]


class QueryRegressionPackTests(unittest.TestCase):
    def test_head_torso_tail_queries_rank_expected_sessions_first(self):
        ag = _load_agsearch()
        rows = _fixture_rows()
        cases = [
            ("stripe webhook", "sid_head_exact"),
            ("eu legislation", "sid_torso_stem"),
            ("alibrry flag", "sid_typo_target"),
        ]
        for query, want_sid in cases:
            with self.subTest(query=query):
                ranked = ag.rank_sessions(rows, ag.parse_query(query), usage={}, now=0)
                self.assertGreater(len(ranked), 0)
                self.assertEqual(ranked[0][2][ag.C_SID], want_sid)

    def test_tail_typo_query_matches_both_concepts(self):
        ag = _load_agsearch()
        rows = _fixture_rows()
        ranked = ag.rank_sessions(rows, ag.parse_query("alibrry flag"), usage={}, now=0)
        self.assertEqual(ranked[0][2][ag.C_SID], "sid_typo_target")
        self.assertEqual(ranked[0][1], 2)  # typo-resolved "alibrry" + exact "flag"

    def test_stopword_heavy_query_reduces_to_signal_term(self):
        ag = _load_agsearch()
        rows = _fixture_rows()
        qterms = ag.parse_query("how migration")
        self.assertEqual([w for w, _s in qterms], ["migration"])
        ranked = ag.rank_sessions(rows, qterms, usage={}, now=0)
        self.assertEqual(ranked[0][2][ag.C_SID], "sid_migration")

    def test_unseen_query_returns_no_matches(self):
        ag = _load_agsearch()
        rows = _fixture_rows()
        ranked = ag.rank_sessions(rows, ag.parse_query("quantum unicorn"), usage={}, now=0)
        self.assertEqual(ranked, [])


if __name__ == "__main__":
    unittest.main()
