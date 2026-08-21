"""The searched blob is stored lowercased.

Ranking is its only reader, and lowercasing it per query meant re-lowering the entire corpus
on every keystroke of a live filter: measured at over half of all ranking time.
"""

import os
import tempfile
import unittest

from load_agsearch import load_agsearch


def _message_row(ag, sid, ts, role, title, text):
    # sid, cwd, branch, ts, role, seq, title, text, kind
    return ag.SEP.join([sid, "/repo", "main", ts, role, "0", title, text, "cli"])


class IndexCaseTests(unittest.TestCase):
    def _build(self, ag, lines):
        d = tempfile.mkdtemp()
        ag.CACHE_DIR = d        # build_sessions derives sessions.tsv from the mode's cache dir
        ag.INDEX_PATH = os.path.join(d, "index.json")
        ag.build_sessions(lines)
        sessions_path = ag.cache_paths(False)[2]
        rows = [l.split(ag.SEP) for l in open(sessions_path).read().splitlines() if l]
        return [r for r in rows if len(r) >= ag.SESSION_COLS]

    def test_blob_is_written_lowercased(self):
        ag = load_agsearch()
        rows = self._build(ag, [
            _message_row(ag, "sid1", "2026-08-19T00:00:00", "user", "Deploy Notes",
                         "The SECRETS-SCAN job merges Gitleaks and TruffleHog"),
        ])
        blob = rows[0][ag.C_BLOB]
        self.assertEqual(blob, blob.lower())
        self.assertIn("secrets-scan", blob)
        self.assertIn("trufflehog", blob)

    def test_uppercase_source_text_is_still_findable(self):
        ag = load_agsearch()
        rows = self._build(ag, [
            _message_row(ag, "sid_hit", "2026-08-19T00:00:00", "user", "Deploy Notes",
                         "The SECRETS-SCAN job merges Gitleaks and TruffleHog"),
            _message_row(ag, "sid_miss", "2026-08-19T00:00:00", "user", "Other",
                         "nothing related to that at all"),
        ])
        ranked = ag.rank_sessions(rows, ag.parse_query("TruffleHog"), usage={}, now=0)
        self.assertEqual([r[2][ag.C_SID] for r in ranked], ["sid_hit"])

    def test_title_keeps_its_original_case_for_display(self):
        ag = load_agsearch()
        rows = self._build(ag, [
            _message_row(ag, "sid1", "2026-08-19T00:00:00", "user", "Deploy Notes", "body text"),
        ])
        self.assertEqual(rows[0][ag.C_TITLE], "Deploy Notes")


if __name__ == "__main__":
    unittest.main()
