"""Gold-list scorer: rank_sessions on a frozen sessions.tsv snapshot.

Personal labels live at ~/.cache/agsearch/gold.jsonl (do not commit).
Snapshot: ~/.cache/agsearch/gold-sessions.tsv

  python3 tests/test_gold_scorer.py snapshot   (freezes rows + usage + clock)
  python3 tests/test_gold_scorer.py rank "how migration"
  python3 tests/test_gold_scorer.py score
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

from load_agsearch import load_agsearch

GOLD_SESSIONS_NAME = "gold-sessions.tsv"
GOLD_JSONL_NAME = "gold.jsonl"
GOLD_META_NAME = "gold-meta.json"


def gold_sessions_path(ag) -> str:
    return os.path.join(ag.CACHE_DIR, GOLD_SESSIONS_NAME)


def gold_meta_path(ag) -> str:
    return os.path.join(ag.CACHE_DIR, GOLD_META_NAME)


def gold_jsonl_path(ag) -> str:
    return os.path.join(ag.CACHE_DIR, GOLD_JSONL_NAME)


def load_snapshot_rows(ag, path=None):
    path = path or gold_sessions_path(ag)
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"missing frozen snapshot {path}\n"
            "copy once: python3 tests/test_gold_scorer.py snapshot"
        )
    rows = []
    with open(path, errors="replace") as fh:
        for line in fh:
            if line.count(ag.SEP) >= ag.SESSION_COLS - 1:
                rows.append(line.rstrip("\n").split(ag.SEP))
    return rows


def load_snapshot_meta(ag, path=None):
    """Frozen usage counts + clock captured with the snapshot.

    Without these the score drifts with no code change: `_usage_counts()` grows every time
    you resume anything, and recency decay moves every day. A ranking delta measured against
    a moving baseline means nothing, so a missing meta file is an error, not a fallback.
    """
    path = path or gold_meta_path(ag)
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"missing frozen snapshot meta {path}\n"
            "re-snapshot once: python3 tests/test_gold_scorer.py snapshot"
        )
    with open(path) as fh:
        meta = json.load(fh)
    return meta.get("usage", {}), meta.get("now")


def rank_sids(ag, rows, query, usage=None, now=None):
    """Rank against the snapshot. usage/now default to the frozen meta, never live state."""
    if usage is None and now is None:
        usage, now = load_snapshot_meta(ag)
    ranked = ag.rank_sessions(rows, ag.parse_query(query), usage=usage or {}, now=now)
    return [item[2][ag.C_SID] for item in ranked]


def accepted_sids(rec):
    """The sids that satisfy this query.

    Sessions get continued, duplicated and forked, so more than one can be the right answer.
    Pinning exactly one then scores a MISS for returning an equally good session, which makes
    every ranking delta measured against this list a little bit wrong. `expected_sids` takes a
    list; `expected_sid` stays valid for the single-answer case.
    """
    if rec.get("expected_sids"):
        return list(rec["expected_sids"])
    return [rec["expected_sid"]]


def recall_at_1(expected, ranked_sids):
    """expected is a sid or a list of acceptable sids."""
    if not ranked_sids:
        return False
    if isinstance(expected, str):
        return ranked_sids[0] == expected
    return ranked_sids[0] in expected


def same_title_hit(ag, rows_by_sid, expected, top_sid):
    """Did we return a different session carrying the SAME title as an accepted one?

    Reported next to the strict number rather than folded into it. Identical titles are a
    proxy for "the user would have been happy", not proof, so it stays a diagnostic: a wide
    gap between the two columns means the labels need splitting, not that ranking improved.
    """
    if isinstance(expected, str):
        expected = [expected]
    titles = {rows_by_sid[s][ag.C_TITLE] for s in expected if s in rows_by_sid}
    top = rows_by_sid.get(top_sid)
    return bool(top) and top[ag.C_TITLE] in titles


def snapshot_live_sessions(ag, now=None):
    """Freeze the corpus AND the two query-independent boosts that feed _boost()."""
    src = ag.SESSIONS_PATH
    dest = gold_sessions_path(ag)
    if not os.path.isfile(src):
        raise FileNotFoundError(f"no live sessions table at {src}; run agsearch once first")
    os.makedirs(ag.CACHE_DIR, exist_ok=True)
    shutil.copyfile(src, dest)
    with open(gold_meta_path(ag), "w") as fh:
        json.dump({"now": time.time() if now is None else now,
                   "usage": ag._usage_counts()}, fh, indent=2, sort_keys=True)
    return dest


def load_gold_jsonl(path):
    out = []
    with open(path, errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


class GoldScorerTests(unittest.TestCase):
    def test_missing_snapshot_errors(self):
        ag = load_agsearch()
        missing = os.path.join(tempfile.mkdtemp(), "nope.tsv")
        with self.assertRaises(FileNotFoundError) as ctx:
            load_snapshot_rows(ag, missing)
        self.assertIn("missing frozen snapshot", str(ctx.exception))

    def test_missing_meta_errors_instead_of_using_live_state(self):
        ag = load_agsearch()
        missing = os.path.join(tempfile.mkdtemp(), "nope.json")
        with self.assertRaises(FileNotFoundError) as ctx:
            load_snapshot_meta(ag, missing)
        self.assertIn("missing frozen snapshot meta", str(ctx.exception))

    def test_a_list_of_acceptable_sids_counts_as_a_hit(self):
        ag = load_agsearch()
        self.assertTrue(recall_at_1(["sid_a", "sid_b"], ["sid_b", "sid_a"]))
        self.assertFalse(recall_at_1(["sid_a", "sid_b"], ["sid_c", "sid_a"]))

    def test_single_expected_sid_still_works(self):
        self.assertEqual(accepted_sids({"expected_sid": "sid_a"}), ["sid_a"])
        self.assertEqual(accepted_sids({"expected_sid": "sid_a",
                                        "expected_sids": ["sid_a", "sid_b"]}),
                         ["sid_a", "sid_b"])

    def test_same_title_is_reported_separately_not_counted_as_a_hit(self):
        ag = load_agsearch()
        rows = {
            "sid_want": ["sid_want", "/r", "2026-08-19", "cc", "cli", "Compass migration", "x", "y"],
            "sid_twin": ["sid_twin", "/r", "2026-08-19", "cc", "cli", "Compass migration", "x", "y"],
            "sid_other": ["sid_other", "/r", "2026-08-19", "cc", "cli", "Unrelated", "x", "y"],
        }
        self.assertTrue(same_title_hit(ag, rows, "sid_want", "sid_twin"))
        self.assertFalse(same_title_hit(ag, rows, "sid_want", "sid_other"))
        # and it is not silently folded into recall@1
        self.assertFalse(recall_at_1("sid_want", ["sid_twin"]))

    def test_same_title_check_survives_a_sid_missing_from_the_snapshot(self):
        ag = load_agsearch()
        self.assertFalse(same_title_hit(ag, {}, "sid_gone", "sid_also_gone"))

    def test_frozen_meta_keeps_score_stable_as_usage_grows(self):
        """Same corpus + same frozen meta must rank identically however often you resume."""
        ag = load_agsearch()
        rows = [
            ["sid_a", "/r", "2026-08-19", "cc", "cli", "Stripe", "stripe webhook", "stripe webhook"],
            ["sid_b", "/r", "2026-08-19", "cc", "cli", "Stripe", "stripe webhook", "stripe webhook"],
        ]
        frozen = rank_sids(ag, rows, "stripe webhook", usage={}, now=0)
        resumed_a_lots = rank_sids(ag, rows, "stripe webhook", usage={"sid_b": 50}, now=0)
        self.assertNotEqual(frozen, resumed_a_lots)   # usage really does move @1 ...
        again = rank_sids(ag, rows, "stripe webhook", usage={}, now=0)
        self.assertEqual(frozen, again)               # ... so it has to be pinned

    def test_recall_at_1_on_fixture_gold(self):
        ag = load_agsearch()
        rows = [
            ["sid_a", "/r", "2026-08-19", "cc", "cli", "Stripe", "stripe webhook", "stripe webhook"],
            ["sid_b", "/r", "2026-08-19", "cc", "cli", "Other", "other", "unrelated"],
        ]
        sids = rank_sids(ag, rows, "stripe webhook", usage={}, now=0)
        self.assertEqual(sids[0], "sid_a")
        self.assertTrue(recall_at_1("sid_a", sids))
        self.assertFalse(recall_at_1("sid_b", sids))


def _cmd_rank(query):
    ag = load_agsearch()
    rows = load_snapshot_rows(ag)
    sids = rank_sids(ag, rows, query)
    print(f"query\t{query}")
    for i, sid in enumerate(sids[:5], 1):
        print(f"{i}\t{sid}")
    if not sids:
        print("0\t(no matches)")


def _cmd_score():
    ag = load_agsearch()
    path = gold_jsonl_path(ag)
    if not os.path.isfile(path):
        raise SystemExit(f"missing {path} — add JSONL lines: {{\"query\":\"...\",\"expected_sid\":\"...\"}}")
    rows = load_snapshot_rows(ag)
    gold = load_gold_jsonl(path)
    by_sid = {r[ag.C_SID]: r for r in rows}
    hits = tolerant = 0
    for rec in gold:
        sids = rank_sids(ag, rows, rec["query"])
        accepted = accepted_sids(rec)
        ok = recall_at_1(accepted, sids)
        top = sids[0] if sids else ""
        dup = (not ok) and same_title_hit(ag, by_sid, accepted, top)
        hits += int(ok)
        tolerant += int(ok or dup)
        ranks = [sids.index(s) + 1 for s in accepted if s in sids]
        rank = min(ranks) if ranks else None
        flag = "OK" if ok else ("DUP" if dup else "MISS")
        print(f"{flag}\t@1={ok}\trank={rank}\t{rec['query']}\t{','.join(accepted)}")
        if dup:
            print(f"\t\tsame title returned instead: {top}"
                  f"  ({by_sid[top][ag.C_TITLE][:60]!r})")
    n = len(gold)
    print(f"recall@1\t{hits}/{n}\t{hits / n if n else 0:.3f}")
    print(f"same-title-tolerant\t{tolerant}/{n}\t{tolerant / n if n else 0:.3f}"
          f"\t(diagnostic: a gap here means labels need splitting)")


def main(argv):
    if argv[:1] == ["snapshot"]:
        ag = load_agsearch()
        dest = snapshot_live_sessions(ag)
        print(dest)
        return 0
    if argv[:1] == ["rank"]:
        _cmd_rank(" ".join(argv[1:]))
        return 0
    if argv[:1] == ["score"]:
        _cmd_score()
        return 0
    if argv:
        print("usage: snapshot | rank <query> | score", file=sys.stderr)
        return 2
    unittest.main()
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main(sys.argv[1:]))
