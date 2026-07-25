#!/usr/bin/env python3
"""Tests for the session-list row markers: live (●) and 'orig dir gone'.

Run with:  python3 -m unittest discover -s tests -v
"""

import io
import os
import re
import json
import shutil
import tempfile
import contextlib
import unittest
import importlib.util
import importlib.machinery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_loader = importlib.machinery.SourceFileLoader("agsearch", os.path.join(REPO, "agsearch"))
ag = importlib.util.module_from_spec(importlib.util.spec_from_loader("agsearch", _loader))
_loader.exec_module(ag)

ANSI = re.compile(r"\033\[[0-9;]*m")


def plain(s):
    return ANSI.sub("", s)


class TestMissingDirs(unittest.TestCase):
    def setUp(self):
        self.live_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.live_dir, True)
        self.dead_dir = os.path.join(self.live_dir, "gone-worktree")

    def test_detects_only_missing_dirs(self):
        self.assertEqual(ag._missing_dirs([self.live_dir, self.dead_dir]), {self.dead_dir})

    def test_blank_cwd_is_not_marked(self):
        self.assertEqual(ag._missing_dirs(["", ""]), set())

    def test_deduplicates_before_stating(self):
        self.assertEqual(ag._missing_dirs([self.dead_dir] * 50), {self.dead_dir})


class TestRowRendering(unittest.TestCase):
    def row(self, **kw):
        args = dict(sid="s1", cwd="/w/proj", date="2026-07-20", source="cc", kind="cli",
                    title="Some session", badge="1/1")
        args.update(kw)
        return ag._row(**args)

    def test_marker_shown_when_dir_is_gone(self):
        self.assertIn("orig dir gone", plain(self.row(dir_gone=True)))

    def test_no_marker_when_dir_exists(self):
        self.assertNotIn("orig dir gone", plain(self.row(dir_gone=False)))

    def test_marker_is_dim_not_a_warning_colour(self):
        body = self.row(dir_gone=True).split(ag.SEP)[2]
        self.assertIn("\033[2morig dir gone\033[0m", body)

    def test_marker_also_renders_on_auto_rows(self):
        self.assertIn("orig dir gone", plain(self.row(kind="auto", dir_gone=True)))

    def test_marker_composes_with_the_live_dot(self):
        out = plain(self.row(active=True, dir_gone=True))
        self.assertIn("●", self.row(active=True, dir_gone=True))
        self.assertIn("orig dir gone", out)

    def test_marker_does_not_change_the_resume_fields(self):
        """AC: purely informational — sid/cwd (what resume uses) are byte-identical."""
        with_mark = self.row(dir_gone=True).split(ag.SEP)
        without = self.row(dir_gone=False).split(ag.SEP)
        self.assertEqual(with_mark[0], without[0])
        self.assertEqual(with_mark[1], without[1])
        self.assertEqual(with_mark[3], without[3])       # active flag, read by run_fzf


class TestFilterIntegration(unittest.TestCase):
    """End to end through cmd_filter: a dead-dir session is marked, a live-dir one is not."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        self.saved = (ag.SESSIONS_PATH, ag.INDEX_PATH, ag.SUBMAP_PATH, ag.CACHE_DIR)
        ag.SESSIONS_PATH = os.path.join(self.d, "sessions.tsv")
        ag.INDEX_PATH = os.path.join(self.d, "index.json")
        ag.SUBMAP_PATH = os.path.join(self.d, "submap.json")
        ag.CACHE_DIR = self.d
        for p in (ag.INDEX_PATH, ag.SUBMAP_PATH):
            with open(p, "w") as fh:
                json.dump({}, fh)
        S = ag.SEP
        self.dead = os.path.join(self.d, "deleted-worktree")
        rows = [
            S.join(["sid-dead", self.dead, "2026-07-20", "cc", "cli", "Dead worktree session",
                    "fix the stripe webhook", "stripe webhook talk"]),
            S.join(["sid-live", self.d, "2026-07-20", "cc", "cli", "Live dir session",
                    "fix the stripe webhook", "stripe webhook talk"]),
        ]
        with open(ag.SESSIONS_PATH, "w") as fh:
            fh.write("\n".join(rows))

    def tearDown(self):
        ag.SESSIONS_PATH, ag.INDEX_PATH, ag.SUBMAP_PATH, ag.CACHE_DIR = self.saved

    def run_filter(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ag.cmd_filter(["_filter", *argv])
        return {l.split(ag.SEP)[0]: plain(l.split(ag.SEP)[2]) for l in buf.getvalue().splitlines()}

    def test_marked_with_a_query(self):
        out = self.run_filter("stripe", "webhook")
        self.assertIn("orig dir gone", out["sid-dead"])
        self.assertNotIn("orig dir gone", out["sid-live"])

    def test_marked_on_the_initial_no_query_list(self):
        out = self.run_filter()
        self.assertIn("orig dir gone", out["sid-dead"])
        self.assertNotIn("orig dir gone", out["sid-live"])

    def test_marked_session_is_still_listed_and_resumable(self):
        """AC: informational only — the row is present and carries a working resume target."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ag.cmd_filter(["_filter", "stripe"])
        row = next(l for l in buf.getvalue().splitlines() if l.startswith("sid-dead"))
        sid, cwd = row.split(ag.SEP)[0], row.split(ag.SEP)[1]
        self.assertEqual(sid, "sid-dead")
        self.assertEqual(cwd, self.dead)
        # resume() would relocate to the nearest surviving ancestor rather than refuse
        self.assertEqual(os.path.realpath(ag._nearest_existing_dir(cwd)),
                         os.path.realpath(self.d))


if __name__ == "__main__":
    unittest.main(verbosity=2)
