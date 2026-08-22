"""The transcript reader: read a session without resuming it.

The point of ctrl-o is to answer "is this the session I meant?" without paying
a CLI start, a context load, and a session you then have to leave. So the two
properties that matter are that it shows the *whole* conversation (the preview
card deliberately shows four turns) and the *whole* text of each turn (the
index truncates to MSG_INDEX_CHARS, which is a search cap, not a reading one).
"""

import io
import json
import os
import re
import tempfile
import unittest
from contextlib import redirect_stdout

from load_agsearch import load_agsearch

strip = lambda s: re.sub(r"\x1b\[[0-9;]*m", "", s)
SID = "3f1c2b90-4d55-4a1e-9c8e-77b0f2a41c33"


def write_session(path, sid, turns):
    """Minimal Claude JSONL: one line per turn."""
    out = []
    for i, (role, text) in enumerate(turns):
        content = text if role == "user" else [{"type": "text", "text": text}]
        out.append(json.dumps({
            "type": role, "sessionId": sid, "cwd": "/tmp/proj",
            "timestamp": f"2026-08-19T00:00:{i:02d}.000Z",
            "message": {"role": role, "content": content},
        }))
    open(path, "w").write("\n".join(out))


class TranscriptTests(unittest.TestCase):
    def _read(self, turns, query=""):
        ag = load_agsearch()
        with tempfile.TemporaryDirectory() as d:
            session = os.path.join(d, SID + ".jsonl")
            write_session(session, SID, turns)
            ag.INDEX_PATH = os.path.join(d, "index.json")
            ag.SUBMAP_PATH = os.path.join(d, "submap.json")
            json.dump({SID: {"source": "cc", "path": session}}, open(ag.INDEX_PATH, "w"))
            json.dump({}, open(ag.SUBMAP_PATH, "w"))
            buf = io.StringIO()
            with redirect_stdout(buf):
                ag.render_transcript(SID, "0", query)
            return strip(buf.getvalue())

    def test_shows_every_turn_not_just_the_previewed_ones(self):
        """The preview card caps at PREVIEW_TURNS. The reader must not."""
        ag = load_agsearch()
        turns = [("user", f"question number {i}") for i in range(ag.PREVIEW_TURNS + 6)]
        out = self._read(turns)
        for i in range(ag.PREVIEW_TURNS + 6):
            self.assertIn(f"question number {i}", out)

    def test_shows_the_full_text_of_a_long_turn(self):
        """MSG_INDEX_CHARS caps what is *searched*; it must not cap what is read."""
        ag = load_agsearch()
        tail = "ENDOFTHEVERYLONGANSWER"
        long = ("x " * ag.MSG_INDEX_CHARS) + tail
        out = self._read([("user", "the ask"), ("assistant", long)])
        self.assertIn(tail, out)

    def test_marks_the_turns_that_match_the_query(self):
        out = self._read([("user", "unrelated chatter"),
                          ("assistant", "the widget regression is in the parser")],
                         query="widget regression")
        marked = [l for l in out.splitlines() if l.startswith("▶")]
        self.assertEqual(len(marked), 1, out)

    def test_marks_nothing_when_there_is_no_query(self):
        out = self._read([("user", "a"), ("assistant", "b")])
        self.assertEqual([l for l in out.splitlines() if l.startswith("▶")], [])

    def test_header_carries_a_reattach_line(self):
        out = self._read([("user", "the ask")])
        self.assertIn("--resume", out)
        self.assertIn(SID, out)

    def test_a_missing_session_says_so_instead_of_raising(self):
        ag = load_agsearch()
        with tempfile.TemporaryDirectory() as d:
            ag.INDEX_PATH = os.path.join(d, "index.json")
            ag.SUBMAP_PATH = os.path.join(d, "submap.json")
            json.dump({}, open(ag.INDEX_PATH, "w"))
            json.dump({}, open(ag.SUBMAP_PATH, "w"))
            buf = io.StringIO()
            with redirect_stdout(buf):
                ag.render_transcript("no-such-sid", "0", "")
            self.assertIn("not found", buf.getvalue())


class BindingTests(unittest.TestCase):
    """ctrl-u and ctrl-d are fzf defaults (unix-line-discard, delete-char/eof).
    Rebinding them takes away "clear the query", which is the edit people reach
    for most in a search box. This is a regression test, not a style rule."""

    def setUp(self):
        self.src = open(os.path.join(os.path.dirname(__file__), "..", "agsearch")).read()

    def test_does_not_rebind_fzf_defaults(self):
        for key in ("ctrl-u", "ctrl-d", "ctrl-a", "ctrl-e", "ctrl-w"):
            self.assertNotIn(f'"{key}:', self.src, f"{key} is an fzf default")

    def test_binds_the_reader_and_the_copy(self):
        self.assertIn("ctrl-o:execute(", self.src)
        self.assertIn("ctrl-y:execute-silent(", self.src)


if __name__ == "__main__":
    unittest.main()
