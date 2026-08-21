"""Resume has to land in the directory Claude filed the session under, and the command we
print for you to run by hand has to be the command we would have run ourselves."""

import json
import os
import re
import shlex
import tempfile
import unittest

from load_agsearch import load_agsearch


def _slug(path):
    return re.sub(r"[^A-Za-z0-9]", "-", path)


class LaunchDirTests(unittest.TestCase):
    def test_walks_up_to_the_dir_whose_slug_matches_the_project(self):
        ag = load_agsearch()
        launch = "/Users/dev/work"
        sub = "/Users/dev/work/app/api"
        session = f"/Users/dev/.claude/projects/{_slug(launch)}/abc.jsonl"
        self.assertEqual(ag._launch_dir(session, sub), launch)

    def test_returns_cwd_itself_when_it_is_already_the_launch_dir(self):
        ag = load_agsearch()
        launch = "/Users/dev/work"
        session = f"/Users/dev/.claude/projects/{_slug(launch)}/abc.jsonl"
        self.assertEqual(ag._launch_dir(session, launch), launch)

    def test_gives_up_rather_than_guessing_when_no_ancestor_matches(self):
        ag = load_agsearch()
        session = "/Users/dev/.claude/projects/-somewhere-else/abc.jsonl"
        self.assertEqual(ag._launch_dir(session, "/Users/dev/work/app"), "")

    def test_missing_inputs_are_not_an_error(self):
        ag = load_agsearch()
        self.assertEqual(ag._launch_dir("", "/Users/dev/work"), "")
        self.assertEqual(ag._launch_dir("/p/-Users-dev-work/a.jsonl", ""), "")


class ResumeCommandTests(unittest.TestCase):
    def test_quotes_directories_containing_spaces(self):
        ag = load_agsearch()
        line = ag.resume_command("/Users/dev/My Work/repo", ["claude", "--resume", "sid"])
        self.assertEqual(line, "cd '/Users/dev/My Work/repo' && claude --resume sid")
        self.assertEqual(shlex.split(line)[1], "/Users/dev/My Work/repo")

    def test_drops_the_cd_when_there_is_no_target(self):
        ag = load_agsearch()
        self.assertEqual(ag.resume_command("", ["codex", "resume", "sid"]), "codex resume sid")


class ResumePlanTests(unittest.TestCase):
    def _with_index(self, ag, entries):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as fh:
            json.dump(entries, fh)
        ag.INDEX_PATH = path
        return path

    def test_codex_sessions_get_the_codex_command_not_claude(self):
        ag = load_agsearch()
        self._with_index(ag, {"sid_cx": {"source": "codex", "path": "/x/rollout.jsonl"}})
        source, bin_, argv, _cwd, _target, _exists = ag.resume_plan("sid_cx", tempfile.gettempdir())
        self.assertEqual((source, bin_), ("codex", "codex"))
        self.assertEqual(argv, ["codex", "resume", "sid_cx"])

    def test_claude_session_resumes_from_the_launch_dir_not_the_recorded_subdir(self):
        ag = load_agsearch()
        with tempfile.TemporaryDirectory() as launch:
            sub = os.path.join(launch, "packages", "api")
            os.makedirs(sub)
            session = f"/fake/projects/{_slug(launch)}/sid_cc.jsonl"
            self._with_index(ag, {"sid_cc": {"source": "cc", "path": session}})
            _s, _b, argv, cwd, target, exists = ag.resume_plan("sid_cc", sub)
            self.assertEqual(argv, ["claude", "--resume", "sid_cc"])
            self.assertEqual(cwd, launch)
            self.assertEqual(target, launch)
            self.assertTrue(exists)

    def test_unknown_session_still_plans_a_claude_resume(self):
        ag = load_agsearch()
        self._with_index(ag, {})
        source, _b, argv, _cwd, _t, _e = ag.resume_plan("sid_missing", tempfile.gettempdir())
        self.assertEqual(source, "cc")
        self.assertEqual(argv, ["claude", "--resume", "sid_missing"])


if __name__ == "__main__":
    unittest.main()
