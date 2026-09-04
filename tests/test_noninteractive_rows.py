"""`-n` is the surface a pipe reads: a script, a coding agent, or an install without fzf.

It used to be its own thing — an AND of raw substrings over *message* rows, sorted by date —
so it had none of the ranking the TUI has and repeated a session once per matching message.
These tests pin the contract that replaced it: same ranker as the list, one entry per session,
led by the session id, and no ANSI unless a terminal is reading.
"""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

from load_agsearch import load_agsearch

ag = load_agsearch()


def msg(sid, text, role="user", ts="2026-08-19T00:00:00", title="Billing migration"):
    return ag.SEP.join([sid, "/repo/app", "main", ts, role, "0", title, text, "cli"])


def run(lines, query):
    """print_matches against a throwaway cache, returning what a pipe would have read."""
    out, err = io.StringIO(), io.StringIO()
    with tempfile.TemporaryDirectory() as d:
        ag.CACHE_DIR = d
        ag.SESSIONS_PATH = os.path.join(d, "sessions.tsv")
        ag.INDEX_PATH = os.path.join(d, "index.json")
        json.dump({}, open(ag.INDEX_PATH, "w"))
        with redirect_stdout(out), redirect_stderr(err):
            code = ag.print_matches(lines, query)
    return code, out.getvalue()


class NonInteractiveTests(unittest.TestCase):
    def test_a_session_appears_once_however_many_messages_match(self):
        lines = [msg("sid1", "please migrate the billing database"),
                 msg("sid1", "the billing database migration is done", role="assistant")]
        _code, out = run(lines, "billing")
        self.assertEqual(out.count("sid1"), 1, out)

    def test_the_entry_leads_with_the_session_id(self):
        """The id is the handle `agsearch read <sid>` takes. Without it a hit is unopenable."""
        _code, out = run([msg("sid1", "please migrate the billing database")], "billing")
        self.assertTrue(out.startswith("sid1 "), out)

    def test_piped_output_carries_no_ansi(self):
        _code, out = run([msg("sid1", "please migrate the billing database")], "billing")
        self.assertNotIn("\x1b", out)

    def test_a_typo_still_finds_the_session(self):
        """Raw substring could not do this, and it is what the README's demo promises."""
        _code, out = run([msg("sid1", "please migrate the billing database")], "databse")
        self.assertIn("sid1", out)

    def test_no_match_says_so_and_exits_nonzero(self):
        code, out = run([msg("sid1", "please migrate the billing database")], "kubernetes")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()
