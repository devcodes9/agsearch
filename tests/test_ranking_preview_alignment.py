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


if __name__ == "__main__":
    unittest.main()
