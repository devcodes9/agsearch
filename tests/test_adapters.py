"""Every harness gets its own row schema, labels and resume command.

The old code answered "which harness is this?" with a ternary in five places, so a source it
did not know about was silently parsed, labelled and resumed as Claude. These tests pin the
table that replaced them, and the two parsers added with it.

Fixtures here are synthetic. Real transcripts are not committed.
"""

import json
import os
import sqlite3
import tempfile
import unittest

from load_agsearch import load_agsearch

ag = load_agsearch()

# TSV columns, per the schema comment in agsearch.
C_SID, C_CWD, C_BRANCH, C_TS, C_ROLE, C_SEQ, C_TITLE, C_TEXT, C_KIND = range(9)


class RegistryTests(unittest.TestCase):
    def test_every_source_is_complete(self):
        keys = {"roots", "match", "parse", "label", "colour", "resume",
                "subagents", "launch_dir"}
        for name, rec in ag.SOURCES.items():
            self.assertEqual(keys, set(rec), name)
            self.assertTrue(callable(rec["parse"]), name)
            self.assertTrue(callable(rec["match"]), name)

    def test_names_are_unique(self):
        names = [r["label"] for r in ag.SOURCES.values()]
        self.assertEqual(len(names), len(set(names)))

    def test_resume_templates_use_a_known_placeholder(self):
        for name, rec in ag.SOURCES.items():
            kind, argv = rec["resume"]
            self.assertIn(kind, ("id", "path"), name)
            self.assertTrue(any("{sid}" in a or "{path}" in a for a in argv), name)

    def test_column_mark_matches_the_turn_name(self):
        """The list column and the assistant-turn label used to be written out separately and
        had drifted. They are now the same string by construction."""
        for name, rec in ag.SOURCES.items():
            self.assertIn(rec["label"], ag._SRC_MARK[name])
            self.assertEqual(rec["label"], ag._agent_name(name))

    def test_source_column_fits_the_longest_name(self):
        """Every row aligns on this column, so a harness whose name overflows it would ragged
        the whole list."""
        for rec in ag.SOURCES.values():
            self.assertLessEqual(len(rec["label"]), ag.SOURCE_COL)

    def test_unknown_source_falls_back_to_claude(self):
        self.assertIs(ag._source("harness-from-the-future"), ag.SOURCES["cc"])


class ResumeRecipeTests(unittest.TestCase):
    def plan(self, source, sid, path):
        d = tempfile.mkdtemp()
        old = ag.INDEX_PATH
        ag.INDEX_PATH = os.path.join(d, "index.json")
        try:
            with open(ag.INDEX_PATH, "w") as fh:
                json.dump({sid: {"source": source, "path": path}}, fh)
            return ag.resume_plan(sid, "")
        finally:
            ag.INDEX_PATH = old

    def test_id_recipe_substitutes_the_session_id(self):
        _s, bin_, argv, _c, _t, _e = self.plan("cursor", "chat-123", "/tmp/x/store.db")
        self.assertEqual("cursor-agent", bin_)
        self.assertEqual(["cursor-agent", "--resume", "chat-123"], argv)

    def test_path_recipe_substitutes_the_transcript_path(self):
        """Gemini's --resume takes a project-scoped index number, which is not a stable handle
        for a session found by search. Resume must go through the file instead."""
        _s, bin_, argv, _c, _t, _e = self.plan("gemini", "sid-1", "/tmp/chats/s.json")
        self.assertEqual(["gemini", "--session-file", "/tmp/chats/s.json"], argv)
        self.assertNotIn("sid-1", argv)

    def test_every_resume_opens_an_interactive_session(self):
        """Each harness has a one-shot form and an interactive form, and they are not the same
        command. `opencode run --session <id>` exits with "You must provide a message"; the
        bare command opens the session. Pin the exact argv so a wrong form is caught here and
        not by a user pressing enter on a result."""
        expected = {
            "cc":       ["claude", "--resume", "ID"],
            "codex":    ["codex", "resume", "ID"],
            "cursor":   ["cursor-agent", "--resume", "ID"],
            "opencode": ["opencode", "--session", "ID"],
            "gemini":   ["gemini", "--session-file", "PATH"],
        }
        self.assertEqual(set(ag.SOURCES), set(expected), "a source has no pinned resume command")
        for source, want in expected.items():
            _s, _b, argv, _c, _t, _e = self.plan(source, "ID", "PATH")
            self.assertEqual(want, argv, source)

    def test_existing_harnesses_are_unchanged(self):
        _s, _b, argv, _c, _t, _e = self.plan("cc", "abc", "/tmp/p/abc.jsonl")
        self.assertEqual(["claude", "--resume", "abc"], argv)
        _s, _b, argv, _c, _t, _e = self.plan("codex", "abc", "/tmp/s/abc.jsonl")
        self.assertEqual(["codex", "resume", "abc"], argv)


def write_gemini(dirpath, messages, project_root="/work/repo"):
    chats = os.path.join(dirpath, "chats")
    os.makedirs(chats, exist_ok=True)
    with open(os.path.join(dirpath, ".project_root"), "w") as fh:
        fh.write(project_root)
    path = os.path.join(chats, "session-2026-01-01T00-00-abcd1234.json")
    with open(path, "w") as fh:
        json.dump({"sessionId": "11111111-2222-3333-4444-555555555555",
                   "projectHash": "deadbeef", "startTime": "2026-01-01T00:00:00.000Z",
                   "lastUpdated": "2026-01-01T00:05:00.000Z", "messages": messages}, fh)
    return path


class GeminiParserTests(unittest.TestCase):
    def parse(self, messages, **kw):
        d = tempfile.mkdtemp()
        return ag.parse_gemini_session(write_gemini(d, messages, **kw))

    def test_rows_use_the_shared_schema(self):
        sid, rows = self.parse([
            {"type": "user", "content": "why does the checksum retry twice"},
            {"type": "gemini", "content": "because the backoff resets"},
        ])
        self.assertEqual("11111111-2222-3333-4444-555555555555", sid)
        self.assertEqual(2, len(rows))
        for i, r in enumerate(rows):
            self.assertEqual(9, len(r))
            self.assertEqual(sid, r[C_SID])
            self.assertEqual("/work/repo", r[C_CWD])
            self.assertEqual(str(i), r[C_SEQ])
            self.assertEqual("cli", r[C_KIND])
        self.assertEqual(["user", "assistant"], [r[C_ROLE] for r in rows])

    def test_cli_chrome_is_not_indexed(self):
        """`info` entries are auth prompts and update notices. Indexing them makes every
        Gemini session match the same words and mean nothing."""
        _sid, rows = self.parse([
            {"type": "info", "content": "Update successful! Waiting for authentication..."},
            {"type": "error", "content": "IneligibleTierError"},
            {"type": "user", "content": "real question"},
        ])
        self.assertEqual(["real question"], [r[C_TEXT] for r in rows])

    def test_title_is_the_first_user_turn(self):
        _sid, rows = self.parse([
            {"type": "gemini", "content": "assistant speaks first"},
            {"type": "user", "content": "the actual task"},
        ])
        self.assertTrue(all(r[C_TITLE] == "the actual task" for r in rows))

    def test_missing_project_root_leaves_cwd_blank(self):
        """Gemini stores a sha256 projectHash, never a path. With no .project_root there is
        nothing to recover, and a guess would be worse than an empty column."""
        d = tempfile.mkdtemp()
        path = write_gemini(d, [{"type": "user", "content": "hi"}])
        os.remove(os.path.join(d, ".project_root"))
        _sid, rows = ag.parse_gemini_session(path)
        self.assertEqual("", rows[0][C_CWD])

    def test_unreadable_file_is_skipped_not_fatal(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "session-broken.json")
        with open(path, "w") as fh:
            fh.write("{not json")
        _sid, rows = ag.parse_gemini_session(path)
        self.assertEqual([], rows)


def write_cursor(chat_id="chat-abc", turns=(), project="tmp", title=None):
    """A Cursor transcript: <project>/agent-transcripts/<id>/<id>.jsonl, one json per line."""
    root = tempfile.mkdtemp()
    chat = os.path.join(root, project, "agent-transcripts", chat_id)
    os.makedirs(chat)
    path = os.path.join(chat, chat_id + ".jsonl")
    with open(path, "w") as fh:
        for entry in turns:
            fh.write(json.dumps(entry) + "\n")
    if title is not None:
        ag._CURSOR_TITLES = {chat_id: title}
    else:
        ag._CURSOR_TITLES = {}
    return path


def cursor_turn(role, text):
    return {"role": role, "message": {"content": [{"type": "text", "text": text}]}}


class CursorParserTests(unittest.TestCase):
    def tearDown(self):
        ag._CURSOR_TITLES = None

    def test_rows_use_the_shared_schema(self):
        db = write_cursor(turns=[
            cursor_turn("user", "<user_query>why is the badge count wrong</user_query>"),
            cursor_turn("assistant", "the filter runs before the join"),
        ], title="Badge Discrepancy")
        sid, rows = ag.parse_cursor_session(db)
        self.assertEqual("chat-abc", sid)
        self.assertEqual(2, len(rows))
        for i, r in enumerate(rows):
            self.assertEqual(9, len(r))
            self.assertEqual("chat-abc", r[C_SID])
            self.assertEqual("Badge Discrepancy", r[C_TITLE])
            self.assertEqual(str(i), r[C_SEQ])
            self.assertTrue(r[C_TS].startswith("20"))
        self.assertEqual(["user", "assistant"], [r[C_ROLE] for r in rows])

    def test_session_id_is_the_resume_handle(self):
        """`cursor-agent --resume <chatId>` takes the file stem, so that is the row key."""
        db = write_cursor(chat_id="7f3f46c7-7c48-43ba-9bd2-8ace1dd6b058",
                          turns=[cursor_turn("user", "hi")])
        sid, _rows = ag.parse_cursor_session(db)
        self.assertEqual("7f3f46c7-7c48-43ba-9bd2-8ace1dd6b058", sid)

    def test_user_turn_is_the_query_not_its_wrapper(self):
        """Cursor surrounds what was typed with attachments, timestamps and skill lists.
        Indexed whole, those swamp the prompt and become the session title."""
        db = write_cursor(turns=[cursor_turn("user",
            "[Image]\n<timestamp>Monday, Aug 3, 2026</timestamp>\n"
            "<user_query>\nfix the retry backoff\n</user_query>")])
        _sid, rows = ag.parse_cursor_session(db)
        self.assertEqual("fix the retry backoff", rows[0][C_TEXT])

    def test_tags_with_attributes_are_stripped(self):
        """The first pattern matched bare tags only, so `<hooks_context description="...">`
        survived and ~50 sessions were titled with injected hook context."""
        db = write_cursor(turns=[cursor_turn("assistant",
            '<hooks_context description="Additional context provided by session hooks">'
            'noise</hooks_context> the real answer')])
        _sid, rows = ag.parse_cursor_session(db)
        self.assertEqual("the real answer", rows[0][C_TEXT])
        self.assertNotIn("hooks_context", rows[0][C_TEXT])

    def test_status_entries_are_not_turns(self):
        db = write_cursor(turns=[{"type": "status", "status": "running"},
                                 {"error": "boom"},
                                 cursor_turn("user", "the only real turn")])
        _sid, rows = ag.parse_cursor_session(db)
        self.assertEqual(["the only real turn"], [r[C_TEXT] for r in rows])

    def test_title_falls_back_to_the_first_user_turn(self):
        db = write_cursor(turns=[cursor_turn("user", "untitled chat topic")], title=None)
        _sid, rows = ag.parse_cursor_session(db)
        self.assertEqual("untitled chat topic", rows[0][C_TITLE])

    def test_missing_file_is_skipped_not_fatal(self):
        _sid, rows = ag.parse_cursor_session(os.path.join(tempfile.mkdtemp(), "gone.jsonl"))
        self.assertEqual([], rows)


class UnslugTests(unittest.TestCase):
    """Cursor names a project directory after its path with non-alphanumerics replaced by `-`,
    which a real dash makes ambiguous. Resolve it against the filesystem, longest match first."""

    def test_resolves_a_directory_containing_a_dash(self):
        root = tempfile.mkdtemp()
        target = os.path.join(root, "my-workspace", "sub")
        os.makedirs(target)
        slug = target.replace(os.sep, "-").strip("-")
        ag._UNSLUG_CACHE.clear()
        self.assertEqual(target, ag._unslug(slug))

    def test_a_directory_that_is_gone_resolves_to_nothing(self):
        ag._UNSLUG_CACHE.clear()
        self.assertEqual("", ag._unslug("no-such-place-anywhere-12345"))


def write_opencode(sessions):
    """sessions: {sid: (directory, title, [(role, [(part_type, text), ...]), ...])}"""
    root = tempfile.mkdtemp()
    db = os.path.join(root, "opencode.db")
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE session (id text PRIMARY KEY, project_id text, directory text, "
                 "title text, time_created integer, time_updated integer)")
    conn.execute("CREATE TABLE message (id text PRIMARY KEY, session_id text, "
                 "time_created integer, data text)")
    conn.execute("CREATE TABLE part (id text PRIMARY KEY, message_id text, session_id text, "
                 "time_created integer, data text)")
    t = 1767225600000
    mn = pn = 0
    for sid, (directory, title, turns) in sessions.items():
        conn.execute("INSERT INTO session VALUES (?,?,?,?,?,?)",
                     (sid, "proj", directory, title, t, t + 60000))
        for role, parts in turns:
            mn += 1
            mid = "msg%d" % mn
            conn.execute("INSERT INTO message VALUES (?,?,?,?)",
                         (mid, sid, t + mn, json.dumps({"role": role})))
            for ptype, text in parts:
                pn += 1
                body = {"type": ptype}
                if text is not None:
                    body["text"] = text
                conn.execute("INSERT INTO part VALUES (?,?,?,?,?)",
                             ("prt%d" % pn, mid, sid, t + pn, json.dumps(body)))
    conn.commit()
    conn.close()
    return db


class OpencodeParserTests(unittest.TestCase):
    def test_one_database_yields_every_session(self):
        """opencode keeps all sessions in a single database. The indexer used to take the
        first row's id as the id for the whole file, which collapsed them into one."""
        db = write_opencode({
            "ses_a": ("/work/one", "First", [("user", [("text", "quasar buffer")])]),
            "ses_b": ("/work/two", "Second", [("user", [("text", "checksum ladder")])]),
        })
        _sid, rows = ag.parse_opencode_session(db)
        self.assertEqual({"ses_a", "ses_b"}, {r[C_SID] for r in rows})
        by = {r[C_SID]: r for r in rows}
        self.assertEqual("/work/one", by["ses_a"][C_CWD])
        self.assertEqual("Second", by["ses_b"][C_TITLE])

    def test_rows_use_the_shared_schema(self):
        db = write_opencode({"ses_a": ("/work", "T", [
            ("user", [("text", "why does it retry")]),
            ("assistant", [("text", "the backoff resets")]),
        ])})
        _sid, rows = ag.parse_opencode_session(db)
        self.assertEqual(["user", "assistant"], [r[C_ROLE] for r in rows])
        for i, r in enumerate(rows):
            self.assertEqual(9, len(r))
            self.assertEqual(str(i), r[C_SEQ])
            self.assertEqual("cli", r[C_KIND])
            self.assertTrue(r[C_TS].startswith("20"))

    def test_only_text_parts_are_indexed(self):
        """A message is made of typed parts. Tool calls and step markers are not conversation,
        and reasoning is only indexed when the user asked for thinking."""
        db = write_opencode({"ses_a": ("/w", "T", [("assistant", [
            ("step-start", None), ("tool", "grep -r foo"),
            ("reasoning", "internal deliberation"), ("text", "the visible answer"),
        ])])})
        _sid, rows = ag.parse_opencode_session(db)
        self.assertEqual(["the visible answer"], [r[C_TEXT] for r in rows])
        _sid, rows = ag.parse_opencode_session(db, include_thinking=True)
        self.assertEqual(["internal deliberation", "the visible answer"],
                         [r[C_TEXT] for r in rows])

    def test_title_falls_back_to_the_first_user_turn(self):
        db = write_opencode({"ses_a": ("/w", "", [("user", [("text", "the real task")])])})
        _sid, rows = ag.parse_opencode_session(db)
        self.assertEqual("the real task", rows[0][C_TITLE])

    def test_missing_database_is_skipped_not_fatal(self):
        sid, rows = ag.parse_opencode_session(os.path.join(tempfile.mkdtemp(), "opencode.db"))
        self.assertEqual("", sid)
        self.assertEqual([], rows)


class SharedDatabaseTests(unittest.TestCase):
    """A parser for a shared database hands back every session it holds. Reading one session
    must show that session only."""

    def test_preview_keeps_only_the_requested_session(self):
        db = write_opencode({
            "ses_a": ("/w", "A", [("user", [("text", "alpha content")])]),
            "ses_b": ("/w", "B", [("user", [("text", "beta content")])]),
        })
        d = tempfile.mkdtemp()
        old_index, old_sub = ag.INDEX_PATH, ag.SUBMAP_PATH
        ag.INDEX_PATH = os.path.join(d, "index.json")
        ag.SUBMAP_PATH = os.path.join(d, "submap.json")
        try:
            with open(ag.INDEX_PATH, "w") as fh:
                json.dump({"ses_a": {"source": "opencode", "path": db},
                           "ses_b": {"source": "opencode", "path": db}}, fh)
            with open(ag.SUBMAP_PATH, "w") as fh:
                json.dump({}, fh)
            source, tagged = ag.load_session_rows("ses_b", False)
            self.assertEqual("opencode", source)
            self.assertEqual(["beta content"], [r[C_TEXT] for r, _sub in tagged])
        finally:
            ag.INDEX_PATH, ag.SUBMAP_PATH = old_index, old_sub


class DiscoveryTests(unittest.TestCase):
    def test_each_harness_matches_only_its_own_files(self):
        """The walk used to accept `.jsonl` globally, which made every non-jsonl transcript
        invisible no matter what the source table said."""
        cases = [
            ("cc", "/p/abc.jsonl", True), ("cc", "/p/store.db", False),
            ("codex", "/s/rollout.jsonl", True),
            ("gemini", "/c/session-2026-01-01T00-00-ab.json", True),
            ("gemini", "/c/logs.json", False),
            # `<id>/<id>.jsonl` is the session; `<id>/subagents/<other>.jsonl` is not, and the
            # two are indistinguishable by filename alone.
            ("cursor", "/p/agent-transcripts/abc/abc.jsonl", True),
            ("cursor", "/p/agent-transcripts/abc/subagents/def.jsonl", False),
            ("cursor", "/p/agent-transcripts/abc/meta.json", False),
            ("opencode", "/o/opencode.db", True), ("opencode", "/o/opencode.db-wal", False)]
        for source, path, want in cases:
            self.assertEqual(want, bool(ag.SOURCES[source]["match"](path)),
                             "%s / %s" % (source, path))


if __name__ == "__main__":
    unittest.main()
