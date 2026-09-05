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
        keys = {"roots", "match", "parse", "tag", "label", "colour", "resume",
                "subagents", "launch_dir"}
        for name, rec in ag.SOURCES.items():
            self.assertEqual(keys, set(rec), name)
            self.assertTrue(callable(rec["parse"]), name)
            self.assertTrue(callable(rec["match"]), name)

    def test_tags_are_unique_and_two_chars(self):
        tags = [r["tag"] for r in ag.SOURCES.values()]
        self.assertEqual(len(tags), len(set(tags)))
        for t in tags:
            self.assertEqual(2, len(t))

    def test_resume_templates_use_a_known_placeholder(self):
        for name, rec in ag.SOURCES.items():
            kind, argv = rec["resume"]
            self.assertIn(kind, ("id", "path"), name)
            self.assertTrue(any("{sid}" in a or "{path}" in a for a in argv), name)

    def test_column_mark_matches_the_turn_tag(self):
        """The list column and the assistant-turn label used to be written out separately and
        had drifted. They are now the same string by construction."""
        for name, rec in ag.SOURCES.items():
            self.assertIn(rec["tag"], ag._SRC_MARK[name])
            self.assertEqual(rec["tag"], ag._agent_tag(name))

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


def write_cursor(chat_id="chat-abc", blobs=(), title="Fixture Chat", cwd="/work/repo"):
    root = tempfile.mkdtemp()
    chat = os.path.join(root, chat_id)
    os.makedirs(chat)
    with open(os.path.join(chat, "meta.json"), "w") as fh:
        json.dump({"schemaVersion": 1, "title": title, "cwd": cwd,
                   "createdAtMs": 1767225600000, "updatedAtMs": 1767225900000}, fh)
    db = os.path.join(chat, "store.db")
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE blobs (id TEXT PRIMARY KEY, data BLOB)")
    for i, b in enumerate(blobs):
        payload = b if isinstance(b, bytes) else json.dumps(b).encode()
        conn.execute("INSERT INTO blobs VALUES (?, ?)", ("b%d" % i, payload))
    conn.commit()
    conn.close()
    return db


class CursorParserTests(unittest.TestCase):
    def test_rows_use_the_shared_schema(self):
        db = write_cursor(blobs=[
            {"role": "user", "content": "why is the badge count wrong"},
            {"role": "assistant", "content": "the filter runs before the join"},
        ])
        sid, rows = ag.parse_cursor_session(db)
        self.assertEqual("chat-abc", sid)
        self.assertEqual(2, len(rows))
        for i, r in enumerate(rows):
            self.assertEqual(9, len(r))
            self.assertEqual("chat-abc", r[C_SID])
            self.assertEqual("/work/repo", r[C_CWD])
            self.assertEqual("Fixture Chat", r[C_TITLE])
            self.assertEqual(str(i), r[C_SEQ])
        self.assertEqual(["user", "assistant"], [r[C_ROLE] for r in rows])

    def test_session_id_is_the_resume_handle(self):
        """`cursor-agent --resume <chatId>` takes the directory name, so that is what the row
        must be keyed by."""
        db = write_cursor(chat_id="7f3f46c7-7c48-43ba-9bd2-8ace1dd6b058",
                          blobs=[{"role": "user", "content": "hi"}])
        sid, _rows = ag.parse_cursor_session(db)
        self.assertEqual("7f3f46c7-7c48-43ba-9bd2-8ace1dd6b058", sid)

    def test_non_message_blobs_are_ignored(self):
        """The blobs table also holds binary merkle nodes, embedded images and the system
        prompt. None of them are conversation."""
        db = write_cursor(blobs=[
            b"\xff\xd8\xff\xe0\x00\x10JFIF binary image",
            b"\n \x9e\x97d\x9d\x8f\xf5(\xab\xe7 merkle node",
            {"role": "system", "content": "You are a coding assistant. " * 50},
            {"role": "user", "content": "the only real turn"},
        ])
        _sid, rows = ag.parse_cursor_session(db)
        self.assertEqual(["the only real turn"], [r[C_TEXT] for r in rows])

    def test_injected_context_is_stripped_from_user_turns(self):
        """Cursor prepends environment blocks to the user turn. Indexed, they make every
        session match 'OS Version' and bury what the human typed."""
        db = write_cursor(blobs=[{
            "role": "user",
            "content": "<user_info>\nOS Version: darwin 25.5.0\n</user_info>\n"
                       "<workspace>/work/repo</workspace>\n"
                       "actually fix the retry backoff",
        }])
        _sid, rows = ag.parse_cursor_session(db)
        self.assertEqual("actually fix the retry backoff", rows[0][C_TEXT])

    def test_every_row_carries_the_session_timestamp(self):
        """Blob order is insertion order; per-message times were never recorded. group_sessions
        takes the max row timestamp, so stamping updatedAtMs dates the session correctly
        without inventing times."""
        db = write_cursor(blobs=[{"role": "user", "content": "a"},
                                 {"role": "assistant", "content": "b"}])
        _sid, rows = ag.parse_cursor_session(db)
        stamps = {r[C_TS] for r in rows}
        self.assertEqual(1, len(stamps))
        self.assertTrue(stamps.pop().startswith("20"))

    def test_missing_store_is_skipped_not_fatal(self):
        _sid, rows = ag.parse_cursor_session(os.path.join(tempfile.mkdtemp(), "store.db"))
        self.assertEqual([], rows)

    def test_title_falls_back_to_the_first_user_turn(self):
        db = write_cursor(title="", blobs=[{"role": "user", "content": "untitled chat topic"}])
        _sid, rows = ag.parse_cursor_session(db)
        self.assertEqual("untitled chat topic", rows[0][C_TITLE])


class DiscoveryTests(unittest.TestCase):
    def test_each_harness_matches_only_its_own_files(self):
        """The walk used to accept `.jsonl` globally, which made every non-jsonl transcript
        invisible no matter what the source table said."""
        cases = [("cc", "abc.jsonl", True), ("cc", "store.db", False),
                 ("codex", "rollout.jsonl", True),
                 ("gemini", "session-2026-01-01T00-00-ab.json", True),
                 ("gemini", "logs.json", False),
                 ("cursor", "store.db", True), ("cursor", "store.db-wal", False),
                 ("cursor", "prompt_history.json", False)]
        for source, name, want in cases:
            self.assertEqual(want, bool(ag.SOURCES[source]["match"](name)),
                             "%s / %s" % (source, name))


if __name__ == "__main__":
    unittest.main()
