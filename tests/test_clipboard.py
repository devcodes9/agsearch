"""The query is copied so ⌘F/^F jumps to it inside the resumed session.

macOS-only `pbcopy` meant that silently did nothing everywhere else, on a tool that otherwise
runs anywhere Python does.
"""

import unittest

from load_agsearch import load_agsearch


class ClipboardTests(unittest.TestCase):
    def _fake(self, available):
        calls = []

        def which(name):
            return f"/usr/bin/{name}" if name in available else None

        def run(cmd, input=None, text=None, check=None):
            calls.append((cmd, input))

        return which, run, calls

    def test_prefers_pbcopy_when_present(self):
        ag = load_agsearch()
        which, run, calls = self._fake({"pbcopy", "xclip"})
        self.assertEqual(ag.copy_to_clipboard("hello", which, run), "pbcopy")
        self.assertEqual(calls, [(["pbcopy"], "hello")])

    def test_falls_through_to_wayland_then_x11(self):
        ag = load_agsearch()
        for available, expected in [({"wl-copy", "xclip"}, "wl-copy"),
                                    ({"xclip"}, "xclip"),
                                    ({"xsel"}, "xsel")]:
            with self.subTest(available=available):
                which, run, calls = self._fake(available)
                self.assertEqual(ag.copy_to_clipboard("q", which, run), expected)
                self.assertEqual(calls[0][0][0], expected)

    def test_passes_the_right_selection_flags(self):
        ag = load_agsearch()
        which, run, calls = self._fake({"xclip"})
        ag.copy_to_clipboard("q", which, run)
        self.assertEqual(calls[0][0], ["xclip", "-selection", "clipboard"])

    def test_no_clipboard_tool_is_not_an_error(self):
        ag = load_agsearch()
        which, run, calls = self._fake(set())
        self.assertEqual(ag.copy_to_clipboard("q", which, run), "")
        self.assertEqual(calls, [])

    def test_a_tool_that_fails_to_launch_does_not_stop_the_next_one(self):
        ag = load_agsearch()
        which, _run, calls = self._fake({"wl-copy", "xclip"})

        def run(cmd, input=None, text=None, check=None):
            if cmd[0] == "wl-copy":
                raise OSError("no wayland display")
            calls.append((cmd, input))

        self.assertEqual(ag.copy_to_clipboard("q", which, run), "xclip")
        self.assertEqual(calls[0][0][0], "xclip")


if __name__ == "__main__":
    unittest.main()
