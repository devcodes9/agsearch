"""How much of each message reaches the index.

_single_line defaults to 400 characters, which is the right length for a preview line and the
wrong one for an index. Called without an explicit limit, it silently truncated every message
at 400: on a real corpus that is 41% of messages cut short and only 19% of all transcript text
searchable. A table or a summary a few hundred characters into a reply was simply absent, so
no ranking change could ever surface it.
"""

import json
import os
import tempfile
import unittest

from load_agsearch import load_agsearch


def _write_session(ag, sid, texts):
    d = tempfile.mkdtemp()
    path = os.path.join(d, f"{sid}.jsonl")
    with open(path, "w") as fh:
        for i, t in enumerate(texts):
            fh.write(json.dumps({
                "type": "assistant", "sessionId": sid, "cwd": "/repo",
                "timestamp": f"2026-08-19T00:00:0{i}",
                "message": {"role": "assistant", "content": t},
            }) + "\n")
    return path


class MessageIndexingTests(unittest.TestCase):
    def test_content_past_400_characters_is_indexed(self):
        ag = load_agsearch()
        buried = "x" * 900 + " secrets-scan merges gitleaks and trufflehog"
        _sid, rows = ag.parse_session(_write_session(ag, "sid1", [buried]))
        text = rows[0][7]
        self.assertIn("trufflehog", text, "content past 400 chars must reach the index")
        self.assertGreater(len(text), 400)

    def test_the_cap_is_explicit_and_still_bounded(self):
        ag = load_agsearch()
        self.assertGreaterEqual(ag.MSG_INDEX_CHARS, 4_000)
        huge = "y" * (ag.MSG_INDEX_CHARS + 5_000)
        _sid, rows = ag.parse_session(_write_session(ag, "sid2", [huge]))
        self.assertEqual(len(rows[0][7]), ag.MSG_INDEX_CHARS)

    def test_a_long_message_makes_its_session_findable(self):
        ag = load_agsearch()
        buried = ("routine preamble that says nothing useful. " * 20
                  + " the zizmor job runs alongside semgrep")
        self.assertGreater(buried.index("zizmor"), 400)
        hit = _write_session(ag, "sid_hit", [buried])
        miss = _write_session(ag, "sid_miss", ["completely unrelated notes about billing"])
        lines = []
        for p in (hit, miss):
            _s, rows = ag.parse_session(p)
            lines += [ag.SEP.join(r) for r in rows]
        d = tempfile.mkdtemp()
        ag.CACHE_DIR = d        # build_sessions derives sessions.tsv from the mode's cache dir
        ag.INDEX_PATH = os.path.join(d, "index.json")
        ag.build_sessions(lines)
        sessions_path = ag.cache_paths(False)[2]
        rows = [l.split(ag.SEP) for l in open(sessions_path).read().splitlines() if l]
        rows = [r for r in rows if len(r) >= ag.SESSION_COLS]
        ranked = ag.rank_sessions(rows, ag.parse_query("zizmor"), usage={}, now=0)
        self.assertEqual([r[2][ag.C_SID] for r in ranked], ["sid_hit"])


if __name__ == "__main__":
    unittest.main()
