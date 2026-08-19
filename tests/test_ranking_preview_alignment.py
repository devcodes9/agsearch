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


class RankingPreviewAlignmentTests(unittest.TestCase):
    def test_exact_line_matches_rank_above_stem_only_hits(self):
        ag = _load_agsearch()
        rows = [
            [
                "s1",
                "/repo/a",
                "2026-08-19",
                "cc",
                "cli",
                "EU legislate strategy deep dive",
                "Need EU policy planning.",
                "Need EU policy planning. · " + ("eu legislate roadmap " * 30),
            ],
            [
                "s2",
                "/repo/b",
                "2026-08-19",
                "cc",
                "cli",
                "notes",
                "eu legislation checklist",
                "eu legislation checklist · eu legislation article summary · eu legislation compliance notes",
            ],
        ]

        qterms = ag.parse_query("EU legislation")
        ranked = ag.rank_sessions(rows, qterms, usage={}, now=0)

        self.assertEqual(ranked[0][2][ag.C_SID], "s2")
        self.assertEqual(ranked[0][1], 2)

    def test_preview_uses_same_normalized_terms_as_ranking(self):
        ag = _load_agsearch()
        rows = [
            [
                "s_top",
                "/repo/a",
                "2026-08-19",
                "cc",
                "cli",
                "Migration mega thread",
                "migration plan",
                "migration checklist · migration steps · migration details · migration rollback",
            ],
            [
                "s_lower",
                "/repo/b",
                "2026-08-18",
                "cc",
                "cli",
                "notes",
                "",
                "how migration works · how migration rollback · migration pitfalls",
            ],
        ]

        query = "how migration"
        qterms = ag.parse_query(query)
        ranked = ag.rank_sessions(rows, qterms, usage={}, now=0)
        self.assertEqual(ranked[0][2][ag.C_SID], "s_top")

        # Regression proof: raw split terms would show 0 top preview hits ("how" is a stopword).
        self.assertEqual(ag._count_line_matches(rows[0][ag.C_BLOB].lower(), query.lower().split()), 0)

        # Fixed behavior: preview and ranking use the same normalized terms.
        preview_terms = ag.preview_match_terms(query)
        self.assertEqual(preview_terms, ag._match_keys(qterms))
        self.assertGreater(ag._count_line_matches(rows[0][ag.C_BLOB].lower(), preview_terms), 0)
        self.assertGreater(ag._count_line_matches(rows[1][ag.C_BLOB].lower(), preview_terms), 0)

    def test_exact_line_strength_is_bounded_before_bm25(self):
        ag = _load_agsearch()
        rows = [
            [
                "s_many_lines",
                "/repo/a",
                "2026-08-19",
                "cc",
                "cli",
                "notes",
                "",
                "eu legislation one · eu legislation two · eu legislation three · "
                "eu legislation four · eu legislation five · eu legislation six",
            ],
            [
                "s_focused",
                "/repo/b",
                "2026-08-19",
                "cc",
                "cli",
                "EU legislation rollout plan",
                "eu legislation migration strategy and policy checklist",
                "eu legislation checklist · eu legislation rollout · eu legislation policy",
            ],
        ]

        qterms = ag.parse_query("EU legislation")
        ranked = ag.rank_sessions(rows, qterms, usage={}, now=0)

        # A stronger title/first-prompt BM25 signal should win once line-hit count is capped.
        self.assertEqual(ranked[0][2][ag.C_SID], "s_focused")


if __name__ == "__main__":
    unittest.main()
