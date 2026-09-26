"""Expired sessions: the transcript is deleted, the text agsearch indexed is kept.

Claude Code deletes transcripts after 30 days by default, and until now agsearch dropped its
index for a session the moment the file went. The cases that matter: the kept copy is small
(no tool output, no automation, capped messages), it is searchable and readable but never
resumed, it ends after EXPIRED_KEEP_DAYS, and a transcript that comes back replaces it.
"""

import datetime
import io
import json
import os
import re
import tempfile
import unittest
from contextlib import redirect_stdout

from load_agsearch import load_agsearch

strip = lambda s: re.sub(r"\x1b\[[0-9;]*m", "", s)


def write_session(d, sid, turns, entrypoint="cli"):
    """A Claude transcript. `turns` is [(role, text)]; role "tool" is a tool result."""
    path = os.path.join(d, sid + ".jsonl")
    with open(path, "w") as fh:
        for i, (role, text) in enumerate(turns):
            if role == "tool":
                content = [{"type": "tool_result", "content": text}]
                role = "user"
            else:
                content = text
            fh.write(json.dumps({
                "type": role, "sessionId": sid, "cwd": "/repo", "entrypoint": entrypoint,
                "timestamp": "2026-08-01T10:%02d:00Z" % i,
                "message": {"role": role, "content": content},
            }) + "\n")
    return path


class ExpiredTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        self.projects = os.path.join(root, "projects")
        os.makedirs(self.projects)
        cache = os.path.join(root, "cache")
        ag = self.ag = load_agsearch()
        ag.CACHE_DIR = cache
        ag.FRAG_DIR = os.path.join(cache, "frag")
        ag.META_PATH = os.path.join(cache, "meta.json")
        ag.SESSIONS_PATH = os.path.join(cache, "sessions.tsv")
        ag.SUBMAP_PATH = os.path.join(cache, "submap.json")
        ag.INDEX_PATH = os.path.join(cache, "index.json")
        ag.FORKS_PATH = os.path.join(cache, "forks.json")
        ag.EXPIRED_DIR = os.path.join(cache, "expired")
        ag.EXPIRED_PATH = os.path.join(cache, "expired.json")
        ag.PROJECTS_DIR = self.projects
        for name, rec in ag.SOURCES.items():
            rec["roots"] = [self.projects] if name == "cc" else []

    def tearDown(self):
        self.tmp.cleanup()

    def index(self):
        return json.load(open(self.ag.INDEX_PATH))

    def expire(self, sid, turns, **kw):
        """Index a session, then delete its transcript and index again."""
        path = write_session(self.projects, sid, turns, **kw)
        self.ag.build_index()
        os.remove(path)
        return self.ag.build_index()

    def test_deleted_transcript_stays_searchable(self):
        lines = self.expire("s1", [("user", "webhook retry backoff?"),
                                   ("assistant", "decided: exponential backoff")])
        rows = self.ag.build_sessions(lines)
        self.assertEqual([f[self.ag.C_SID] for f in rows], ["s1"])
        self.assertEqual(rows[0][self.ag.C_KIND], "expired")
        hits = self.ag.rank_sessions(rows, self.ag.parse_query("exponential backoff"))
        self.assertEqual(hits[0][2][self.ag.C_SID], "s1")
        self.assertEqual(self.index()["s1"]["expired"], datetime.date.today().isoformat())

    def test_kept_copy_drops_tool_output_and_caps_messages(self):
        lines = self.expire("s1", [("user", "hi"), ("tool", "huge tool dump"),
                                   ("assistant", "x" * 10_000)])
        roles = [l.split(self.ag.SEP)[4] for l in lines]
        self.assertEqual(roles, ["user", "assistant"])
        self.assertEqual(len(lines[1].split(self.ag.SEP)[7]), self.ag.EXPIRED_MSG_CHARS)

    def test_automation_runs_are_not_kept(self):
        lines = self.expire("s1", [("user", "review this diff")], entrypoint="sdk-py")
        self.assertEqual(lines, [])
        self.assertNotIn("s1", self.index())

    def test_read_shows_kept_text_and_says_it_cannot_resume(self):
        self.expire("s1", [("user", "webhook retry"), ("assistant", "use backoff")])
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(self.ag.render_transcript("s1", color=False), 0)
        out = strip(buf.getvalue())
        self.assertIn("use backoff", out)
        self.assertIn("cannot be resumed", out)
        self.assertNotIn("--resume", out)

    def test_row_is_tagged_expired(self):
        lines = self.expire("s1", [("user", "webhook retry")])
        f = self.ag.build_sessions(lines)[0]
        row = self.ag._row(f[0], f[1], f[2], f[3], f[4], f[5], "    ")
        self.assertIn("expired webhook retry", strip(row))

    def test_kept_copy_ends_after_keep_days(self):
        self.expire("s1", [("user", "webhook retry")])
        later = datetime.date.today() + datetime.timedelta(days=self.ag.EXPIRED_KEEP_DAYS + 1)
        lines = self.ag._keep_expired(set(), set(), {}, {}, today=later)
        self.assertEqual(lines, [])
        self.assertEqual(os.listdir(self.ag.EXPIRED_DIR), [])

    def test_restored_transcript_replaces_kept_copy(self):
        turns = [("user", "webhook retry"), ("tool", "tool text")]
        self.expire("s1", turns)
        write_session(self.projects, "s1", turns)
        lines = self.ag.build_index()
        self.assertNotIn("expired", self.index()["s1"])
        self.assertEqual(len(lines), 2)              # the live copy only, tool row included
        self.assertEqual(os.listdir(self.ag.EXPIRED_DIR), [])

    def test_subagent_turns_stay_labelled_as_subagent(self):
        write_session(self.projects, "s1", [("user", "main prompt")])
        sub = os.path.join(self.projects, "agent-x1.jsonl")
        with open(sub, "w") as fh:
            fh.write(json.dumps({"type": "user", "sessionId": "s1", "cwd": "/repo",
                                 "timestamp": "2026-08-01T11:00:00Z",
                                 "message": {"role": "user", "content": "subagent task"}}))
        self.ag.build_index()
        os.remove(sub)
        os.remove(os.path.join(self.projects, "s1.jsonl"))
        self.ag.build_index()
        _source, tagged = self.ag.load_session_rows("s1")
        self.assertEqual([(r[7], s) for r, s in tagged],
                         [("main prompt", False), ("subagent task", True)])

    def test_copy_in_an_old_layout_is_dropped_not_misread(self):
        self.expire("s1", [("user", "webhook retry")])
        kept = json.load(open(self.ag.EXPIRED_PATH))
        for v in kept.values():
            v["fmt"] = self.ag.EXPIRED_FMT - 1
        json.dump(kept, open(self.ag.EXPIRED_PATH, "w"))
        self.assertEqual(self.ag.build_index(), [])
        self.assertNotIn("s1", self.index())

    def test_fragments_from_an_older_cache_format_are_not_saved(self):
        path = write_session(self.projects, "s1", [("user", "webhook retry")])
        self.ag.build_index()
        meta = json.load(open(self.ag.META_PATH))
        meta["_fmt"] = self.ag.CACHE_FMT - 1
        json.dump(meta, open(self.ag.META_PATH, "w"))
        os.remove(path)
        self.assertEqual(self.ag.build_index(), [])

    def test_forced_rebuild_still_notices_the_deletion(self):
        path = write_session(self.projects, "s1", [("user", "webhook retry")])
        self.ag.build_index()
        os.remove(path)
        self.ag.build_index(force=True)
        self.assertIn("expired", self.index()["s1"])


if __name__ == "__main__":
    unittest.main()
