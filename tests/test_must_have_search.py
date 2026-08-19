import importlib.machinery
import importlib.util
import json
import pathlib
import tempfile
import unittest


def _load_agsearch():
    root = pathlib.Path(__file__).resolve().parents[1]
    path = root / "agsearch"
    loader = importlib.machinery.SourceFileLoader("agsearch_under_test", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class MustHaveSearchTests(unittest.TestCase):
    def test_no_match_guidance_includes_recovery_paths(self):
        ag = _load_agsearch()
        line = "\t".join([
            "sid-1", "/repo/proj", "main", "2026-08-19T00:00:00Z",
            "user", "0", "Session title", "Discuss legislation changes", "cli"
        ])
        guidance = ag._no_match_guidance([line], "how legislation")
        self.assertTrue(any(m.startswith('No matches for "how legislation".') for m in guidance))
        self.assertTrue(any("concept terms:" in m and "legislat" in m for m in guidance))
        self.assertTrue(any("try fuzzy:" in m for m in guidance))
        self.assertTrue(any("recent sessions:" in m for m in guidance))

    def test_record_search_event_logs_normalized_terms(self):
        ag = _load_agsearch()
        with tempfile.NamedTemporaryFile(mode="w+", delete=True) as fh:
            ag._record_search_event(
                "no-fzf",
                "how migration",
                4,
                selected_sid="sid-123",
                selected_rank=2,
                latency_ms=17,
                path=fh.name,
            )
            fh.flush()
            fh.seek(0)
            row = json.loads(fh.readline())
        self.assertEqual(row["mode"], "no-fzf")
        self.assertEqual(row["match_terms"], ["migrat"])
        self.assertEqual(row["result_count"], 4)
        self.assertEqual(row["selected_sid"], "sid-123")
        self.assertEqual(row["selected_rank"], 2)

    def test_result_count_and_rank_for_selected_session(self):
        ag = _load_agsearch()
        rows = [
            ["sid-old", "/repo/a", "2026-08-18", "cc", "cli", "notes", "", "other text only"],
            ["sid-hit", "/repo/b", "2026-08-19", "cc", "cli", "legislation task", "", "legislation plan"],
        ]
        count, rank = ag._result_count_and_rank(rows, "legislation", "sid-hit")
        self.assertEqual(count, 1)
        self.assertEqual(rank, 1)


if __name__ == "__main__":
    unittest.main()
