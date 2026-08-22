"""Cold-build progress line.

Several seconds of silence on first run reads as "hung". The line that fixes
that has to be careful about where it writes: warm runs must stay silent, and
anything piped (`agsearch -n "q" | ...`, the fzf preview subprocess) must not
receive escape codes.
"""

import io
import unittest

from load_agsearch import load_agsearch


class FakeTTY(io.StringIO):
    def isatty(self):
        return True


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.ag = load_agsearch()

    def _run(self, total, stream, ticks=None):
        p = self.ag._IndexProgress(total, stream=stream)
        for _ in range(total if ticks is None else ticks):
            p.tick()
        p.done_()
        return p

    def test_silent_when_stderr_is_not_a_tty(self):
        """Piped output stays byte-clean — this is what keeps `-n` scriptable."""
        buf = io.StringIO()                      # StringIO.isatty() is False
        self._run(500, buf)
        self.assertEqual(buf.getvalue(), "")

    def test_silent_on_a_warm_run(self):
        """A couple of changed sessions re-parse instantly; narrating that is noise."""
        buf = FakeTTY()
        self._run(self.ag.PROGRESS_MIN_FILES - 1, buf)
        self.assertEqual(buf.getvalue(), "")

    def test_reports_on_a_cold_build(self):
        buf = FakeTTY()
        self._run(200, buf)
        out = buf.getvalue()
        self.assertIn("indexing 1/200 sessions...", out)
        self.assertIn("indexing 200/200 sessions...", out)

    def test_repaints_in_place_rather_than_scrolling(self):
        buf = FakeTTY()
        self._run(200, buf)
        out = buf.getvalue()
        self.assertNotIn("\n", out)
        self.assertTrue(out.startswith("\r"))

    def test_leaves_no_residue_above_the_results(self):
        """done_() must erase the line, or it sits above the TUI forever."""
        buf = FakeTTY()
        self._run(200, buf)
        self.assertTrue(buf.getvalue().endswith("\r"))
        tail = buf.getvalue().rsplit("\r", 2)[1]
        self.assertEqual(tail.strip(), "")

    def test_repaint_count_is_bounded_on_a_large_corpus(self):
        """~1% steps: a 5,000-session corpus must not emit 5,000 writes."""
        buf = FakeTTY()
        self._run(5000, buf)
        self.assertLessEqual(buf.getvalue().count("indexing"), 120)

    def test_done_is_idempotent(self):
        buf = FakeTTY()
        p = self._run(200, buf)
        before = buf.getvalue()
        p.done_()
        self.assertEqual(buf.getvalue(), before)

    def test_final_count_shows_even_when_it_is_not_on_a_step_boundary(self):
        buf = FakeTTY()
        self._run(157, buf)
        self.assertIn("indexing 157/157 sessions...", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
