"""`-n` piped is read by a program, and a program pays per character.

A terminal gets aligned columns and the whole session id. A pipe gets neither: alignment buys
an agent nothing, every run of spaces costs it a token, and a 36-char uuid is the most
expensive field on the line for the one reader that has to copy it. These tests pin the
shortened id, the missing padding, the line that names the next command, and the prefix
resolution that makes the shortened id usable.
"""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

from load_agsearch import load_agsearch

ag = load_agsearch()

UUID4 = ["b94c7836-09ee-4716-878a-26a1a407df6f", "fa131384-8585-461b-a951-07a822c00547"]
# Codex writes uuidv7. The leading bytes are a timestamp, so sessions recorded in the same
# period agree on their first 8 characters and disagree only later.
UUID7 = ["019ebbc6-2fbe-7902-abf4-378d68a24645", "019ebbc6-96de-7503-9c1b-b66beb6b88e5"]


def msg(sid, text, role="user", ts="2026-08-19T00:00:00", title="Billing migration"):
    return ag.SEP.join([sid, "/repo/app", "main", ts, role, "0", title, text, "cli"])


def run(lines, query):
    out, err = io.StringIO(), io.StringIO()
    with tempfile.TemporaryDirectory() as d:
        ag.CACHE_DIR = d
        ag.SESSIONS_PATH = os.path.join(d, "sessions.tsv")
        ag.INDEX_PATH = os.path.join(d, "index.json")
        json.dump({}, open(ag.INDEX_PATH, "w"))
        with redirect_stdout(out), redirect_stderr(err):
            code = ag.print_matches(lines, query)
    return code, out.getvalue()


def resolve(sids, prefix):
    with tempfile.TemporaryDirectory() as d:
        ag.INDEX_PATH = os.path.join(d, "index.json")
        json.dump({s: {"source": "cc"} for s in sids}, open(ag.INDEX_PATH, "w"))
        return ag.resolve_sid(prefix)


class ShortIdTests(unittest.TestCase):
    def test_eight_characters_is_not_enough_for_codex_ids(self):
        """The reason the floor exists. Truncate uuidv7 at 8 and two sessions become one."""
        self.assertEqual(len({s[:8] for s in UUID7}), 1)

    def test_the_short_id_still_tells_every_session_apart(self):
        n = ag._short_id_len(UUID4 + UUID7)
        self.assertEqual(len({s[:n] for s in UUID4 + UUID7}), 4)

    def test_the_short_id_is_never_shorter_than_the_floor(self):
        self.assertGreaterEqual(ag._short_id_len(["a" * 36]), ag.AGENT_ID_MIN)

    def test_the_cut_lands_on_a_uuid_group_boundary(self):
        """A prefix cut mid-group reads as noise rather than as an identifier."""
        self.assertIn(ag._short_id_len(UUID4 + UUID7), (13, 18, 23, 36))

    def test_a_corpus_that_needs_the_whole_id_gets_it(self):
        near = ["a" * 35 + "0", "a" * 35 + "1"]
        self.assertEqual(ag._short_id_len(near), 36)


class PipedRowTests(unittest.TestCase):
    def test_the_piped_row_carries_no_column_padding(self):
        _code, out = run([msg("sid1", "please migrate the billing database")], "billing")
        self.assertNotIn("  ", out.splitlines()[0])

    def test_a_terminal_still_gets_aligned_columns(self):
        f = msg("sid1", "please migrate the billing database").split(ag.SEP)
        head = ag._match_entry(f, 1, 1, [], [], 36, True).splitlines()[0]
        self.assertIn("  ", head)

    def test_the_piped_id_is_shortened(self):
        _code, out = run([msg(UUID4[0], "please migrate the billing database")], "billing")
        self.assertTrue(out.startswith(UUID4[0][:13] + " "), out)
        self.assertNotIn(UUID4[0], out)

    def test_the_output_names_the_command_that_opens_a_hit(self):
        """The next thing a program wants is one of these sessions. Say so in the output."""
        _code, out = run([msg("sid1", "please migrate the billing database")], "billing")
        self.assertIn("agsearch read", out)


class ElideTests(unittest.TestCase):
    """A capped `read` has to drop the right turns, not merely few enough of them."""

    def blocks(self, n, size=100):
        return [f"{i:03d}" + "x" * (size - 3) for i in range(n)]

    def test_a_transcript_inside_the_budget_is_untouched(self):
        b = self.blocks(5)
        self.assertEqual(ag._elide(b, 10_000), (b, 0))

    def test_the_opening_and_the_ending_survive(self):
        """What were we doing, and where did we stop."""
        b = self.blocks(50)
        kept, dropped = ag._elide(b, 1000)
        self.assertIn(b[0], kept)
        self.assertIn(b[-1], kept)
        self.assertEqual(dropped, 50 - len(kept))

    def test_matched_turns_outrank_the_ending(self):
        """Asking what was said about X and getting the last twenty messages is a wrong answer."""
        b = self.blocks(50)
        kept, _dropped = ag._elide(b, 1000, matched=[20, 21, 22])
        for i in (20, 21, 22):
            self.assertIn(b[i], kept)

    def test_kept_turns_stay_in_order(self):
        b = self.blocks(50)
        kept, _dropped = ag._elide(b, 1000, matched=[30, 10])
        self.assertEqual(kept, [x for x in b if x in set(kept)])

    def test_a_budget_smaller_than_one_turn_still_returns(self):
        b = self.blocks(10)
        kept, dropped = ag._elide(b, 1)
        self.assertEqual(len(kept) + dropped, 10)


class ResolveSidTests(unittest.TestCase):
    def test_a_whole_id_resolves_to_itself(self):
        self.assertEqual(resolve(UUID4, UUID4[0]), (UUID4[0], None))

    def test_a_unique_prefix_resolves(self):
        self.assertEqual(resolve(UUID4, UUID4[0][:13]), (UUID4[0], None))

    def test_an_ambiguous_prefix_says_how_many_and_what_to_do(self):
        sid, err = resolve(UUID7, UUID7[0][:8])
        self.assertIsNone(sid)
        self.assertIn("2 sessions", err)
        self.assertIn("more characters", err)

    def test_an_unknown_prefix_points_at_search(self):
        sid, err = resolve(UUID4, "zzzz")
        self.assertIsNone(sid)
        self.assertIn("agsearch -n", err)


if __name__ == "__main__":
    unittest.main()
