import inspect
import json
import os
import re
import shlex
import tempfile
import unittest

from load_agsearch import load_agsearch

ag = load_agsearch()


def session_row(sid="s1", cwd="/repo", date="2026-08-20", source="cc", kind="cli",
                title="t", first="f", blob="b"):
    return [sid, cwd, date, source, kind, title, first, blob]


class RelAgeTests(unittest.TestCase):
    """The list column answers 'how long ago', so the buckets have to be the ones people ask in."""

    def test_buckets(self):
        now = ag.time.mktime(ag.time.strptime("2026-08-21", "%Y-%m-%d")) + 3600
        cases = [("2026-08-21", "today"), ("2026-08-20", "1d"), ("2026-08-16", "5d"),
                 ("2026-08-07", "2w"), ("2026-05-21", "3mo"), ("2024-08-21", "2y")]
        for date, want in cases:
            self.assertEqual(ag.rel_age(date, now), want, date)

    def test_undated_never_reads_as_recent(self):
        self.assertEqual(ag.rel_age(""), "?")


# Clipboard behaviour is covered by tests/test_clipboard.py against the shared helper.


class TabLauncherTests(unittest.TestCase):
    """A tab in the terminal you already have, not another window — the whole point of ctrl-t."""

    def _which_all(self, exe):
        return "/usr/bin/" + exe

    def test_tmux_window_when_inside_tmux(self):
        argv = ag.tab_launcher("run me", env={"TMUX": "/tmp/s", "SHELL": "/bin/zsh"},
                               which=self._which_all)
        self.assertEqual(argv, ["tmux", "new-window", "run me"])

    def test_kitty_and_wezterm_use_their_own_cli(self):
        kitty = ag.tab_launcher("run", env={"KITTY_WINDOW_ID": "1", "SHELL": "/bin/zsh"},
                                which=self._which_all)
        self.assertEqual(kitty[:4], ["kitty", "@", "launch", "--type=tab"])
        wez = ag.tab_launcher("run", env={"TERM_PROGRAM": "WezTerm", "SHELL": "/bin/zsh"},
                              which=self._which_all)
        self.assertEqual(wez[:3], ["wezterm", "cli", "spawn"])

    def test_iterm_script_makes_a_tab_when_a_window_exists(self):
        argv = ag.tab_launcher("run", env={"TERM_PROGRAM": "iTerm.app", "SHELL": "/bin/zsh"},
                               which=lambda e: None, platform="darwin", has_iterm=True)
        script = argv[2]
        self.assertEqual(argv[:2], ["osascript", "-e"])
        self.assertIn("create tab with default profile", script)
        self.assertIn("create window with default profile", script)   # only when none is open

    def test_hotkey_launch_with_no_term_program_still_picks_iterm(self):
        self.assertEqual(ag.pick_terminal(env={}, which=lambda e: None,
                                          platform="darwin", has_iterm=True), "iterm")
        self.assertEqual(ag.pick_terminal(env={}, which=lambda e: None,
                                          platform="darwin", has_iterm=False), "terminal")

    def test_env_override_wins_and_substitutes_the_command(self):
        argv = ag.tab_launcher("agsearch --here",
                               env={"AGSEARCH_TERMINAL_CMD": "myterm -e {cmd}"})
        self.assertEqual(argv, ["sh", "-c", "myterm -e 'agsearch --here'"])

    def test_unknown_forced_terminal_reports_failure_instead_of_guessing(self):
        self.assertIsNone(ag.tab_launcher("run", env={"AGSEARCH_TERMINAL": "banana"},
                                          which=lambda e: None, platform="linux"))

    def test_a_project_dir_with_a_space_survives_both_quoting_layers(self):
        with tempfile.TemporaryDirectory() as tmp:
            spaced = os.path.join(tmp, "my project")
            os.mkdir(spaced)
            cmd = ag.resume_command(spaced, ["claude", "--resume", "abc-123"])
            self.assertIn(shlex.quote(spaced), cmd)          # quoted once for the shell
            argv = ag.tab_launcher(cmd, env={"AGSEARCH_TERMINAL_CMD": "t {cmd}"})
            self.assertEqual(argv[:2], ["sh", "-c"])
            self.assertIn("claude --resume abc-123", argv[2])


class ResumeLineTests(unittest.TestCase):
    """ctrl-t and the transcript reader must reattach the same way Enter does.

    resume_line goes through resume_plan, so they inherit the launch-dir fix: resuming from
    the cwd recorded on a message lands in the wrong Claude project for 15% of sessions.
    """

    def _index(self, entries):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as fh:
            json.dump(entries, fh)
        ag.INDEX_PATH = path

    def test_codex_sessions_get_the_codex_command(self):
        self._index({"abc": {"source": "codex", "path": "/x/rollout.jsonl"}})
        self.assertIn("codex resume abc", ag.resume_line("abc", tempfile.gettempdir()))

    def test_claude_sessions_get_the_claude_command(self):
        self._index({"abc": {"source": "cc", "path": "/x/abc.jsonl"}})
        self.assertIn("claude --resume abc", ag.resume_line("abc", tempfile.gettempdir()))

    def test_it_reattaches_from_the_launch_dir_not_the_recorded_subdir(self):
        with tempfile.TemporaryDirectory() as launch:
            sub = os.path.join(launch, "packages", "api")
            os.makedirs(sub)
            slug = re.sub(r"[^A-Za-z0-9]", "-", launch)
            self._index({"abc": {"source": "cc", "path": f"/fake/projects/{slug}/abc.jsonl"}})
            self.assertIn(shlex.quote(launch), ag.resume_line("abc", sub))

    def test_dead_directory_falls_back_instead_of_producing_a_broken_cd(self):
        self._index({"abc": {"source": "cc", "path": "/x/abc.jsonl"}})
        cmd = ag.resume_line("abc", "/tmp/definitely/not/here")
        target = cmd.split(" && ")[0][len("cd "):]
        self.assertTrue(os.path.isdir(target.strip("\'")), cmd)


class TuiStateTests(unittest.TestCase):
    def test_toggles_flip_and_cycle(self):
        st = dict(ag.DEFAULT_TUI_STATE)
        self.assertEqual(ag.toggle_tui_state("here", st)["here"], 1)
        self.assertEqual(ag.toggle_tui_state("auto", st)["auto"], 0)
        self.assertEqual(ag.toggle_tui_state("source", st)["source"], "cc")
        self.assertEqual(ag.toggle_tui_state("source", {"source": "codex"})["source"], "all")
        self.assertEqual(ag.toggle_tui_state("sort", st)["sort"], "recent")

    def test_unreadable_state_falls_back_to_defaults(self):
        self.assertEqual(ag.read_tui_state("/tmp/agsearch-no-such-state.json"),
                         ag.DEFAULT_TUI_STATE)

    def test_scope_source_and_automation_filters(self):
        rows = [session_row("a", cwd="/repo/sub"), session_row("b", cwd="/elsewhere"),
                session_row("c", cwd="/repo", source="codex"),
                session_row("d", cwd="/repo", kind="auto")]
        here = ag.apply_tui_state(rows, {"here": 1, "root": "/repo", "auto": 1, "source": "all"})
        self.assertEqual([r[0] for r in here], ["a", "c", "d"])
        codex = ag.apply_tui_state(rows, {"source": "codex", "auto": 1})
        self.assertEqual([r[0] for r in codex], ["c"])
        mine = ag.apply_tui_state(rows, {"auto": 0, "source": "all"})
        self.assertEqual([r[0] for r in mine], ["a", "b", "c"])


class EmptyStateTests(unittest.TestCase):
    """An empty list must say which key un-hides the sessions, or it reads as a broken index."""

    def test_hint_names_the_toggle_that_is_hiding_things(self):
        row = ag._empty_row({"here": 1, "auto": 1, "source": "all"}, has_query=True)
        self.assertIn("ctrl-s", row)
        self.assertTrue(row.startswith(ag.NO_SID + ag.SEP))

    def test_query_with_no_filters_on_suggests_changing_the_query(self):
        row = ag._empty_row(dict(ag.DEFAULT_TUI_STATE), has_query=True)
        self.assertIn("distinctive words", row)


class SortToggleTests(unittest.TestCase):
    def test_recent_sort_keeps_the_match_set_and_only_reorders_it(self):
        rows = [session_row("old", date="2020-01-01", blob="stripe tax", first="stripe tax"),
                session_row("new", date="2026-08-01", blob="stripe", first="stripe"),
                session_row("none", date="2026-08-20", blob="nothing", first="nothing")]
        qterms = ag.parse_query("stripe tax")
        smart = ag._smart_rows(rows, qterms, sort="smart")
        recent = ag._smart_rows(rows, qterms, sort="recent")
        self.assertEqual(len(smart), 2)                      # 'none' matched nothing, both ways
        self.assertEqual(len(recent), 2)
        self.assertTrue(recent[0].startswith("new"), recent)
        self.assertTrue(smart[0].startswith("old"), smart)   # best match, not newest


class HighlightTests(unittest.TestCase):
    def test_every_occurrence_is_highlighted_not_just_the_first(self):
        out = ag._highlight("gold and gold and GOLD", ["gold"])
        self.assertEqual(out.count("\033[1;30;43m"), 3)

    def test_no_terms_leaves_the_text_untouched(self):
        self.assertEqual(ag._highlight("plain", []), "plain")


class FzfWiringTests(unittest.TestCase):
    """fzf reaches back into this script by name; a typo'd subcommand only shows up at runtime."""

    def test_every_bound_subcommand_is_one_main_dispatches(self):
        args = ag.fzf_args("/bin/agsearch", "0", "0", "")
        used = set(re.findall(r"agsearch (_\w+)", " ".join(args)))
        declared = set(re.findall(r'cmd == "(_\w+)"', inspect.getsource(ag._internal)))
        self.assertTrue(used, "no subcommands found in the fzf bindings")
        self.assertEqual(used - declared, set())

    def test_toggle_keys_reload_and_refresh_the_header(self):
        args = ag.fzf_args("/bin/agsearch", "0", "0", "")
        for key in ("ctrl-s", "ctrl-g", "ctrl-x", "ctrl-r"):
            bind = next(a for a in args if a.startswith(key + ":"))
            self.assertIn("_toggle", bind)
            self.assertIn("reload(", bind)
            self.assertIn("transform-header(", bind)   # else the filter changes invisibly

    def test_header_states_the_current_filters(self):
        on = ag.render_header({"here": 1, "auto": 0, "source": "codex", "sort": "recent"})
        self.assertIn("this project", on)
        self.assertIn("codex only", on)
        self.assertIn("yours only", on)
        self.assertIn("newest first", on)


if __name__ == "__main__":
    unittest.main()
