import importlib.machinery
import importlib.util
import json
import pathlib
import tempfile
import unittest


def _load_agsearch():
    root = pathlib.Path(__file__).resolve().parents[1]
    path = root / "agsearch"
    loader = importlib.machinery.SourceFileLoader("agsearch_under_test", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class ResumeMustHaveTests(unittest.TestCase):
    def test_copy_query_to_clipboard_uses_first_available_command(self):
        ag = _load_agsearch()
        calls = []

        def fake_which(name):
            return "/usr/bin/" + name if name in ("wl-copy", "xclip") else None

        def fake_run(cmd, input, text, check):
            calls.append((cmd, input, text, check))

        used = ag._copy_query_to_clipboard("legislation", which=fake_which, run=fake_run)
        self.assertEqual(used, "wl-copy")
        self.assertEqual(calls[0][0], ["wl-copy"])
        self.assertEqual(calls[0][1], "legislation")

    def test_resume_invocation_is_source_aware(self):
        ag = _load_agsearch()
        with tempfile.TemporaryDirectory() as td:
            idx = pathlib.Path(td) / "index.json"
            idx.write_text(json.dumps({"sid-cc": {"source": "cc"}, "sid-cx": {"source": "codex"}}))
            ag.INDEX_PATH = str(idx)

            source_cc, bin_cc, _argv_cc, _target_cc, _exists_cc, note_cc = ag._resume_invocation("sid-cc", td)
            source_cx, bin_cx, _argv_cx, _target_cx, _exists_cx, note_cx = ag._resume_invocation("sid-cx", td)

            self.assertEqual(source_cc, "cc")
            self.assertEqual(bin_cc, "claude")
            self.assertIn("claude --resume sid-cc", note_cc)
            self.assertEqual(source_cx, "codex")
            self.assertEqual(bin_cx, "codex")
            self.assertIn("codex resume sid-cx", note_cx)

    def test_resume_invocation_falls_back_to_nearest_existing_dir(self):
        ag = _load_agsearch()
        with tempfile.TemporaryDirectory() as td:
            idx = pathlib.Path(td) / "index.json"
            idx.write_text(json.dumps({"sid-cc": {"source": "cc"}}))
            ag.INDEX_PATH = str(idx)
            missing = str(pathlib.Path(td) / "gone" / "nested")

            _source, _bin, _argv, target, exists, note = ag._resume_invocation("sid-cc", missing)
            self.assertFalse(exists)
            self.assertEqual(target, td)
            self.assertTrue(note.startswith(f"cd {td} && claude --resume sid-cc"))


if __name__ == "__main__":
    unittest.main()
