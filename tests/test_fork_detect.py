"""A forked session has to look different from the session it was forked from.

Claude Code forks a conversation by copying the transcript into a new file under a new session
id, and records nothing that says so. The two then sit in the list as separate rows with the
same title, the same project and the same opening prompt, and resuming the wrong one silently
drops everything that happened after the split. The only trace in the format is that copied
messages keep their original uuids, which is what detect_forks reads.
"""

import json
import os
import re
import tempfile
import unittest

from load_agsearch import load_agsearch

ag = load_agsearch()

ANSI = re.compile(r"\033\[[0-9;]*m")


def strip(s):
    return ANSI.sub("", s)


def write_session(d, sid, msgs):
    """One Claude session file. `msgs` is [(uuid, timestamp)] — the rest is filler."""
    path = os.path.join(d, sid + ".jsonl")
    with open(path, "w") as fh:
        for i, (uuid, ts) in enumerate(msgs):
            role = "user" if i % 2 == 0 else "assistant"
            fh.write(json.dumps({
                "type": role, "uuid": uuid, "sessionId": sid, "cwd": "/repo",
                "timestamp": ts, "message": {"role": role, "content": "turn %d" % i},
            }) + "\n")
    return path


def index_of(d, sessions):
    """{sid: [(uuid, ts)]} -> the index shape build_index writes, files included."""
    index = {}
    for sid, msgs in sessions.items():
        path = write_session(d, sid, msgs)
        index[sid] = {"source": "cc", "path": path, "root": ag._root_uuid(path)}
    return index


def turns(uuids, start=0):
    return [(u, "2026-08-19T%02d:00:00.000Z" % (start + i)) for i, u in enumerate(uuids)]


class DetectForkTests(unittest.TestCase):
    def _detect(self, sessions):
        with tempfile.TemporaryDirectory() as d:
            return ag.detect_forks(index_of(d, sessions))

    def test_the_branch_that_continued_second_is_the_fork(self):
        # Both carry a-b-c; the trunk went on at 03:00 and the fork was made at 09:00.
        forks = self._detect({
            "trunk": turns(["a", "b", "c"]) + turns(["t1", "t2"], start=3),
            "later": turns(["a", "b", "c"]) + turns(["f1", "f2"], start=9),
        })
        self.assertEqual(forks, {"later": {"of": "trunk", "at": 3}})

    def test_an_abandoned_trunk_is_not_the_fork(self):
        # The original was forked from and never touched again, so everything it holds is
        # shared. Length is not the signal: the fork is much longer than what it came from.
        forks = self._detect({
            "stub": turns(["a", "b"]),
            "carried_on": turns(["a", "b"]) + turns(["c", "d", "e"], start=5),
        })
        self.assertEqual(forks, {"carried_on": {"of": "stub", "at": 2}})

    def test_a_fork_of_a_fork_points_at_the_fork(self):
        forks = self._detect({
            "first": turns(["a", "b"]) + turns(["p1"], start=2),
            "second": turns(["a", "b"]) + turns(["s1", "s2"], start=4),
            "third": turns(["a", "b"]) + turns(["s1", "s2"], start=4) + turns(["x"], start=8),
        })
        self.assertEqual(forks["second"], {"of": "first", "at": 2})
        self.assertEqual(forks["third"], {"of": "second", "at": 4})

    def test_unrelated_sessions_are_not_a_family(self):
        self.assertEqual(self._detect({
            "one": turns(["a", "b", "c"]),
            "two": turns(["x", "y", "z"]),
        }), {})

    def test_sessions_that_only_share_a_later_message_are_not_a_family(self):
        # The fingerprint is the FIRST message. Sharing something further in is not a fork.
        self.assertEqual(self._detect({
            "one": turns(["a", "shared"]),
            "two": turns(["b", "shared"]),
        }), {})

    def test_codex_sessions_are_never_forks(self):
        with tempfile.TemporaryDirectory() as d:
            index = index_of(d, {"one": turns(["a"]), "two": turns(["a"])})
            for info in index.values():
                info["source"] = "codex"
            self.assertEqual(ag.detect_forks(index), {})

    def test_an_implausibly_large_family_is_treated_as_a_collision(self):
        same = {"s%d" % i: turns(["a", "b"]) for i in range(ag.FORK_FAMILY_MAX + 2)}
        self.assertEqual(self._detect(same), {})


class ForkDisplayTests(unittest.TestCase):
    def _row(self, forked):
        return strip(ag._row("sid", "/repo/app", "2026-08-19", "cc", "cli", "Some title",
                             "    ", forked=forked))

    def test_the_row_says_fork_only_when_it_is_one(self):
        self.assertIn("fork", self._row(True))
        self.assertNotIn("fork", self._row(False))

    def test_the_mark_comes_before_the_title(self):
        """The list pane is a fraction of the terminal, so anything after the title is cut.

        A fork carries the same long title as the session it came from, which is exactly the
        row where the title runs long enough to be truncated. Trailing the title, the mark was
        invisible below a ~200 column terminal.
        """
        row = self._row(True)
        self.assertLess(row.index("fork"), row.index("Some title"))

    def test_the_header_flags_the_fork_ahead_of_the_title(self):
        """Same word in the same place as the list row it was selected from."""
        with tempfile.TemporaryDirectory() as d:
            forks_path = ag.FORKS_PATH
            ag.FORKS_PATH = os.path.join(d, "forks.json")
            try:
                json.dump({"kid": {"of": "0f21fa0f", "at": 41}}, open(ag.FORKS_PATH, "w"))
                self.assertEqual(strip(ag.fork_mark("kid")), "fork ")
                self.assertEqual(ag.fork_mark("someone-else"), "")
            finally:
                ag.FORKS_PATH = forks_path

    def test_the_header_clause_names_the_original_and_the_split(self):
        with tempfile.TemporaryDirectory() as d:
            forks_path = ag.FORKS_PATH
            ag.FORKS_PATH = os.path.join(d, "forks.json")
            try:
                json.dump({"kid": {"of": "0f21fa0f-3074-4864-b949-e7d75449a373", "at": 41}},
                          open(ag.FORKS_PATH, "w"))
                self.assertEqual(ag.fork_line("kid"), " · fork of 0f21fa0f at msg 41")
                self.assertEqual(ag.fork_line("someone-else"), "")
            finally:
                ag.FORKS_PATH = forks_path

    def test_a_missing_fork_map_costs_nothing(self):
        forks_path = ag.FORKS_PATH
        ag.FORKS_PATH = "/nonexistent/forks.json"
        try:
            self.assertEqual(ag.load_forks(), {})
            self.assertEqual(ag.fork_line("anything"), "")
        finally:
            ag.FORKS_PATH = forks_path


if __name__ == "__main__":
    unittest.main()
