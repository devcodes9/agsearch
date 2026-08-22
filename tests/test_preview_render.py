import re
import unittest

from load_agsearch import load_agsearch

ANSI = re.compile(r"\033\[[0-9;]*m")


def strip(s):
    return ANSI.sub("", s)


def row(role, text, seq, date="2026-08-19T00:00:00", title=""):
    # TSV columns: 0 sid 1 cwd 2 branch 3 date 4 role 5 seq 6 title 7 text
    return ["sid", "/repo", "main", date, role, str(seq), title, text]


def tagged(*turns):
    """turns: (role, text[, is_sub]) → list of (row, is_sub), chronological."""
    out = []
    for i, t in enumerate(turns):
        role, text = t[0], t[1]
        is_sub = t[2] if len(t) > 2 else False
        out.append((row(role, text, i), is_sub))
    return out


class PreviewRenderTests(unittest.TestCase):
    def test_query_mode_anchors_opening_prompt_before_deep_match(self):
        ag = load_agsearch()
        t = tagged(
            ("user", "help me set up the billing database"),
            ("assistant", "sure, creating tables"),
            ("user", "now add a stripe webhook handler"),
            ("assistant", "added the webhook handler"),
        )
        lines = [strip(l) for l in ag._preview_lines(t, ["webhook"], "cc")]
        body = "\n".join(lines)
        # opening user prompt shows even though the match is a later turn
        self.assertIn("help me set up the billing database", body)
        # and a divider separates the anchor from the matches
        self.assertIn("⋯", body)
        # match count header present
        self.assertRegex(body, r"● \d+ match")

    def test_query_matches_are_chronological(self):
        ag = load_agsearch()
        t = tagged(
            ("user", "first webhook question"),
            ("assistant", "irrelevant"),
            ("user", "second webhook question"),
        )
        lines = [strip(l) for l in ag._preview_lines(t, ["webhook"], "cc")]
        body = "\n".join(lines)
        self.assertLess(body.index("first webhook"), body.index("second webhook"))

    def test_agent_turns_labelled_by_source(self):
        ag = load_agsearch()
        t = tagged(("user", "hi"), ("assistant", "hello there"))
        cc = "\n".join(strip(l) for l in ag._preview_lines(t, [], "cc"))
        cx = "\n".join(strip(l) for l in ag._preview_lines(t, [], "codex"))
        self.assertIn("you", cc)
        self.assertIn("claude", cc)
        self.assertNotIn("codex", cc)
        self.assertIn("codex", cx)
        self.assertNotIn("claude", cx)

    def test_subagent_turn_is_marked(self):
        ag = load_agsearch()
        t = tagged(("user", "run a webhook check"), ("assistant", "webhook ran", True))
        body = "\n".join(strip(l) for l in ag._preview_lines(t, ["webhook"], "cc"))
        self.assertIn("⤷", body)

    def test_truncates_with_more_line(self):
        ag = load_agsearch()
        turns = [("user", f"webhook item {i}") for i in range(9)]
        t = tagged(*turns)
        body = "\n".join(strip(l) for l in ag._preview_lines(t, ["webhook"], "cc"))
        self.assertRegex(body, r"… \d+ more")

    def test_no_query_arc_shows_opening_and_last(self):
        ag = load_agsearch()
        t = tagged(
            ("user", "opening prompt about migration"),
            ("assistant", "middle reply one"),
            ("assistant", "middle reply two"),
            ("assistant", "final wrap up message"),
        )
        body = "\n".join(strip(l) for l in ag._preview_lines(t, [], "cc"))
        self.assertIn("opening prompt about migration", body)
        self.assertIn("final wrap up message", body)
        # a gap exists between opening exchange and the last turn → divider
        self.assertIn("⋯", body)

    def test_single_message_session_renders_one_turn(self):
        ag = load_agsearch()
        t = tagged(("user", "just one message"))
        body = "\n".join(strip(l) for l in ag._preview_lines(t, [], "cc"))
        self.assertIn("just one message", body)
        self.assertNotIn("⋯", body)


if __name__ == "__main__":
    unittest.main()
