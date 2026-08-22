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


class FmtRowTests(unittest.TestCase):
    def test_assistant_row_is_named_after_the_source(self):
        self.assertIn("cx ", strip(ag.fmt_row(row("assistant", "the reply"), (), "codex")))
        self.assertIn("cc ", strip(ag.fmt_row(row("assistant", "the reply"), (), "cc")))

    def test_source_only_renames_the_agent_side(self):
        for source in ("cc", "codex"):
            self.assertIn("you", strip(ag.fmt_row(row("user", "the ask"), (), source)))
            self.assertIn("th ", strip(ag.fmt_row(row("thinking", "musing"), (), source)))

    def test_defaults_to_claude_when_no_source_is_passed(self):
        self.assertIn("cc ", strip(ag.fmt_row(row("assistant", "the reply"))))


class LabelTests(unittest.TestCase):
    def test_preview_label_follows_the_source(self):
        self.assertEqual(strip(ag._label("assistant", "codex")), "cx ")
        self.assertEqual(strip(ag._label("assistant", "cc")), "cc ")
        self.assertEqual(strip(ag._label("assistant")), "cc ")

    def test_non_agent_roles_are_unchanged(self):
        self.assertEqual(strip(ag._label("user", "codex")), "you")
        self.assertEqual(strip(ag._label("thinking", "codex")), "th ")


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

    def test_matched_codex_turn_is_labelled_cx(self):
        out = self._preview("widget regression")
        self.assertIn("cx ", out)
        self.assertNotIn("cc ", out)

    def test_codex_bookends_are_labelled_cx(self):
        out = self._preview("")           # no query → the opened-with / last card
        self.assertIn("cx ", out)
        self.assertNotIn("cc ", out)


if __name__ == "__main__":
    unittest.main()
