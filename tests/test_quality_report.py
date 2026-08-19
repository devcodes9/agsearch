import importlib.machinery
import importlib.util
import io
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


class QualityReportTests(unittest.TestCase):
    def test_quality_stats_aggregates_core_metrics(self):
        ag = _load_agsearch()
        events = [
            {"query": "alpha", "result_count": 0, "latency_ms": 10},
            {"query": "alpha", "result_count": 2, "selected_sid": "s1", "selected_rank": 1, "latency_ms": 20},
            {"query": "beta", "result_count": 1, "selected_sid": "s2", "selected_rank": 3, "latency_ms": 30},
            {"query": "gamma", "result_count": 0},
        ]
        s = ag._quality_stats(events)
        self.assertEqual(s["total"], 4)
        self.assertEqual(s["zero"], 2)
        self.assertEqual(s["selected"], 2)
        self.assertEqual(s["top_zero_queries"][0], ("alpha", 1))
        self.assertEqual(s["top_queries"][0], ("alpha", 2))
        self.assertEqual(s["ranks"], [1.0, 3.0])
        self.assertEqual(len(s["latencies"]), 3)

    def test_cmd_quality_report_handles_missing_log(self):
        ag = _load_agsearch()
        out = io.StringIO()
        rc = ag.cmd_quality_report(path="/tmp/does-not-exist-agsearch-log.jsonl", out=out)
        self.assertEqual(rc, 0)
        txt = out.getvalue()
        self.assertIn("agsearch quality report", txt)
        self.assertIn("no telemetry events found yet", txt)

    def test_cmd_quality_report_renders_summary(self):
        ag = _load_agsearch()
        with tempfile.NamedTemporaryFile(mode="w+", delete=True) as fh:
            fh.write(json.dumps({"query": "alpha", "result_count": 0, "latency_ms": 11}) + "\n")
            fh.write(json.dumps({"query": "alpha", "result_count": 2, "selected_sid": "s1",
                                 "selected_rank": 2, "latency_ms": 15}) + "\n")
            fh.write("{not-json}\n")
            fh.flush()
            out = io.StringIO()
            rc = ag.cmd_quality_report(path=fh.name, out=out)
        self.assertEqual(rc, 0)
        txt = out.getvalue()
        self.assertIn("events: 2", txt)
        self.assertIn("zero-result rate: 1/2 (50.0%)", txt)
        self.assertIn("selection rate: 1/2 (50.0%)", txt)
        self.assertIn("avg selected rank: 2.00", txt)
        self.assertIn("top zero-result queries:", txt)
        self.assertIn("alpha", txt)


if __name__ == "__main__":
    unittest.main()
