#!/usr/bin/env python3
"""Snippet-rendering tests for agsearch.

Run with:  python3 -m unittest discover -s tests -v

Fixtures are shaped like the real corpus: markdown-heavy assistant prose, JSON tool dumps,
pasted-image placeholders, code fences, and long opaque tokens.
"""

import os
import re
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


class TestCleanSnippet(unittest.TestCase):
    def test_strips_bold_italic_and_code_spans(self):
        self.assertEqual(
            ag.clean_snippet("**Verdict: approve** — the *core* claim holds, see `env.ts`"),
            "Verdict: approve — the core claim holds, see env.ts")

    def test_strips_headings_and_list_markers(self):
        self.assertEqual(ag.clean_snippet("# Document Analysis Yes, this exists"),
                         "Document Analysis Yes, this exists")
        self.assertEqual(ag.clean_snippet("- **Chat schema**: only one field"),
                         "Chat schema: only one field")
        self.assertEqual(ag.clean_snippet("1. run the migration"), "run the migration")

    def test_keeps_prose_dashes_and_underscores(self):
        """A dash between words is not a bullet, and snake_case is not emphasis."""
        self.assertEqual(ag.clean_snippet("the flag - off by default - guards my_var and MAX_LEN"),
                         "the flag - off by default - guards my_var and MAX_LEN")

    def test_link_syntax_becomes_the_link_text(self):
        self.assertEqual(ag.clean_snippet("see [the billing doc](https://example.com/a/b) for why"),
                         "see the billing doc for why")

    def test_code_fence_becomes_placeholder(self):
        out = ag.clean_snippet("here is the fix ```ts const x = 1; export default x; ``` done")
        self.assertEqual(out, "here is the fix [code] done")

    def test_unterminated_fence_is_condensed(self):
        """Messages are capped at 400 chars at index time, so fences are often cut off."""
        out = ag.clean_snippet("patch below ```python def f():  return 1  # truncated mid-fence")
        self.assertEqual(out, "patch below [code]")

    def test_json_dump_becomes_placeholder(self):
        raw = ('{"commits":12,"files":[{"add":0,"del":6,"f":".eslintignore"},'
               '{"add":5,"del":1,"f":".licensed.yml"}]} that is the diff summary')
        self.assertEqual(ag.clean_snippet(raw), "[json] that is the diff summary")

    def test_short_inline_object_is_left_alone(self):
        self.assertEqual(ag.clean_snippet('returns {"ok":true} on success'),
                         'returns {"ok":true} on success')

    def test_truncated_json_is_still_condensed(self):
        raw = 'Links: [{"title":"Multi-Currency Billing for Global SaaS Teams","url":"https://ya'
        self.assertEqual(ag.clean_snippet(raw), "Links: [json]")

    def test_image_placeholder_is_condensed(self):
        raw = "[Image: source: /Users/x/.claude/image-cache/cb0aa939-14b9/2.png] what do you think"
        self.assertEqual(ag.clean_snippet(raw), "[image] what do you think")

    def test_long_opaque_token_is_truncated(self):
        out = ag.clean_snippet("sha " + "a" * 80 + " done")
        self.assertEqual(out, "sha " + "a" * 20 + "… done")

    def test_numbered_file_dump_becomes_placeholder(self):
        raw = ('1 import Stripe from "stripe"; 2 import { env } from "@/env"; 3 4 export type '
               'StripeMode = "test"; 5 6 const clients = {}; and that is the file')
        self.assertTrue(ag.clean_snippet(raw).startswith("[file] "))

    def test_prose_numbered_list_is_not_a_file_dump(self):
        raw = "steps: 1. run the migration 2. build 3. deploy 4. ship it"
        self.assertEqual(ag.clean_snippet(raw), raw)

    def test_c_comments_and_globs_survive(self):
        """Emphasis stripping must not shred /** comments */ or src/**/*.ts globs."""
        raw = "/* eslint-disable no-console */ /** Sync rows */ glob src/**/*.ts and a*b"
        self.assertEqual(ag.clean_snippet(raw), raw)

    def test_whitespace_is_collapsed_and_single_line(self):
        self.assertEqual(ag.clean_snippet("a\n\n  b\tc   d"), "a b c d")

    def test_empty_input(self):
        self.assertEqual(ag.clean_snippet(""), "")


class TestSnippetWindow(unittest.TestCase):
    def test_term_is_highlighted_and_present(self):
        out = ag._snippet("**the stripe webhook** signature was wrong", ["stripe"], 200)
        self.assertIn("stripe", plain(out))
        self.assertIn("\033[1;30;43mstripe\033[0m", out)
        self.assertNotIn("**", plain(out))

    def test_term_inside_a_condensed_dump_still_shows(self):
        """AC: the search term appears in every snippet — even if cleaning would have eaten it."""
        raw = '{"tool":"grep","result":"stripe webhook signature mismatch in checkout.ts here"}'
        out = ag._snippet(raw, ["mismatch"], 200)
        self.assertIn("mismatch", plain(out))
        self.assertIn("\033[1;30;43mmismatch\033[0m", out)

    def test_window_is_centered_on_the_match(self):
        raw = ("filler " * 60) + "the stripe webhook fired " + ("tail " * 60)
        out = plain(ag._snippet(raw, ["stripe"], 120))
        self.assertIn("stripe", out)
        self.assertTrue(out.startswith("…"))

    def test_width_is_stable_across_rows(self):
        """AC: snippet width/line count stays stable — one line, never wider than asked."""
        rows = [
            "short one",
            "**bold** prose that runs on " * 40,
            '{"a":1,"b":2,"c":[1,2,3],"d":"' + "x" * 300 + '"}',
            "```js " + ("const x = 1; " * 60) + "```",
        ]
        for raw in rows:
            out = plain(ag._snippet(raw, ["prose"], 120))
            self.assertNotIn("\n", out)
            self.assertLessEqual(len(out), 120 + 2)      # + leading/trailing ellipsis

    def test_no_query_still_renders_clean_prose(self):
        out = plain(ag._snippet("## Summary **all good** here", [], 200))
        self.assertEqual(out, "Summary all good here")


class TestFmtRow(unittest.TestCase):
    def build_line(self, text):
        return ag.SEP.join(["sid", "/w/proj", "main", "2026-07-20T10:00:00Z", "assistant",
                            "3", "Some title", text])

    def test_row_is_one_stable_line(self):
        noisy = '{"files":[{"f":"a.ts","add":1},{"f":"b.ts","add":2}]} ' + ("blah " * 300)
        out = plain(ag.fmt_row(self.build_line(noisy), ["blah"]))
        self.assertNotIn("\n", out)
        self.assertIn("[json]", out)
        self.assertLessEqual(len(out), 90 + ag.ROW_TEXT_WIDTH + 2)

    def test_row_highlights_the_term(self):
        out = ag.fmt_row(self.build_line("we fixed the **stripe** webhook"), ["stripe"])
        self.assertIn("\033[1;30;43mstripe\033[0m", out)

    def test_row_without_terms_still_works(self):
        out = plain(ag.fmt_row(self.build_line("# heading **bold**")))
        self.assertTrue(out.endswith("heading bold"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
