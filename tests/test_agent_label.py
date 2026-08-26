"""A Codex session marked `cx` in the list must not call itself `cc` everywhere else.

The list column is keyed on the session's source, but the row and preview role labels used to
hardcode `cc` for every assistant turn. On a Codex session the two disagreed on screen, which
reads as "the preview is showing me a different session".
"""

import io
import json
import os
import re
import tempfile
import unittest
from contextlib import redirect_stdout

from load_agsearch import load_agsearch

ag = load_agsearch()

ANSI = re.compile(r"\033\[[0-9;]*m")


def strip(s):
    return ANSI.sub("", s)


def row(role, text, sid="s1", ts="2026-08-19T00:00:00", title="Session title"):
    return ag.SEP.join([sid, "/tmp/proj", "main", ts, role, "0", title, text])


class AgentTagTests(unittest.TestCase):
    def test_codex_is_cx_and_claude_is_cc(self):
        self.assertEqual(ag._agent_tag("codex"), "cx")
        self.assertEqual(ag._agent_tag("cc"), "cc")

    def test_unknown_source_falls_back_to_cc(self):
        self.assertEqual(ag._agent_tag(""), "cc")
        self.assertEqual(ag._agent_tag(None), "cc")


class LabelTests(unittest.TestCase):
    """The preview names the agent in the turn gutter, so these assert the
    rendered gutter rather than a label helper. The list and `-n` paths keep the
    two-character `cc`/`cx` form; only the preview spells the agent out.

    `-n` lists sessions rather than messages, so it has no per-turn role to name; its `cc`/`cx`
    comes from the session's source via _agent_tag, covered by AgentTagTests above."""

    def _gutter(self, source):
        # _preview_lines takes split rows, not the SEP-joined strings row() builds.
        turns = [(row("user", "the ask").split(ag.SEP), False),
                 (row("assistant", "the reply").split(ag.SEP), False)]
        return "\n".join(strip(l) for l in ag._preview_lines(turns, [], source))

    def test_preview_names_the_agent_after_the_source(self):
        self.assertIn("codex", self._gutter("codex"))
        self.assertNotIn("claude", self._gutter("codex"))
        self.assertIn("claude", self._gutter("cc"))
        self.assertNotIn("codex", self._gutter("cc"))

    def test_the_user_side_is_never_renamed(self):
        for source in ("cc", "codex"):
            self.assertIn("you", self._gutter(source))


def write_codex_session(path, sid):
    """Minimal Codex rollout file: session_meta + one user turn + one assistant turn."""
    entries = [
        {"type": "session_meta",
         "payload": {"id": sid, "cwd": "/tmp/proj", "timestamp": "2026-08-19T00:00:00"}},
        {"type": "response_item", "timestamp": "2026-08-19T00:00:01",
         "payload": {"type": "message", "role": "user",
                     "content": [{"text": "find the widget regression"}]}},
        {"type": "response_item", "timestamp": "2026-08-19T00:00:02",
         "payload": {"type": "message", "role": "assistant",
                     "content": [{"text": "the widget regression is in the parser"}]}},
    ]
    with open(path, "w") as fh:
        fh.write("\n".join(json.dumps(e) for e in entries))


class PreviewSourceTests(unittest.TestCase):
    """End to end through render_preview, the pane where the mismatch was visible."""

    def _preview(self, query):
        sid = "9dd3510a-948f-426d-8117-cd31884c0374"
        with tempfile.TemporaryDirectory() as d:
            session = os.path.join(d, sid + ".jsonl")
            write_codex_session(session, sid)
            index_path, submap_path = ag.INDEX_PATH, ag.SUBMAP_PATH
            ag.INDEX_PATH = os.path.join(d, "index.json")
            ag.SUBMAP_PATH = os.path.join(d, "submap.json")
            json.dump({sid: {"source": "codex", "path": session}}, open(ag.INDEX_PATH, "w"))
            json.dump({}, open(ag.SUBMAP_PATH, "w"))
            try:
                buf = io.StringIO()
                with redirect_stdout(buf):
                    ag.render_preview(sid, "0", query)
                return strip(buf.getvalue())
            finally:
                ag.INDEX_PATH, ag.SUBMAP_PATH = index_path, submap_path

    def test_matched_codex_turn_is_named_codex(self):
        out = self._preview("widget regression")
        self.assertIn("codex", out)
        self.assertNotIn("claude", out)

    def test_codex_arc_is_named_codex(self):
        out = self._preview("")           # no query → the conversation arc
        self.assertIn("codex", out)
        self.assertNotIn("claude", out)


if __name__ == "__main__":
    unittest.main()
