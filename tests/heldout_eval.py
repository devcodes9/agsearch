"""Compare ranking candidates on two sets at once, so a change cannot be tuned to the labels.

    python3 tests/heldout_eval.py main ./agsearch candidate /tmp/agsearch-patched

Set 1 is the hand-labelled gold list (15 queries, high signal, easy to overfit).
Set 2 is derived from the corpus itself: take content words out of a session's own title and
require that session back. It covers 300 sessions instead of 15 and nobody tuned against it,
so a change that helps set 1 while flat or down on set 2 is a change fitted to the labels.

The timing column matters as much as the quality columns: fzf re-ranks on every keystroke, so
a variant that buys accuracy at 5x the latency is not shippable.
"""
import os, sys, json, time, random, importlib.machinery, importlib.util
sys.path.insert(0, os.path.abspath("tests"))
from test_gold_scorer import load_snapshot_rows, load_snapshot_meta, gold_jsonl_path, load_gold_jsonl

def load(path, name):
    l = importlib.machinery.SourceFileLoader(name, path)
    sp = importlib.util.spec_from_loader(l.name, l)
    m = importlib.util.module_from_spec(sp); l.exec_module(m); return m

def heldout_queries(ag, rows, seed=7, n=300):
    """Pick content words from a session's own title. If you typed words from the title,
    that session should come back. Titles are not what the ranker mainly scores (body is),
    so this is a fair proxy, and it covers 300 sessions instead of 15."""
    rnd = random.Random(seed)
    pool = []
    for r in rows:
        title = r[ag.C_TITLE]
        if title.startswith("<command-message>"):    # slash-command invocations, not conversations
            continue
        words = [w for w in ag.parse_query(title)]
        if len(words) < 2:
            continue
        pool.append((r[ag.C_SID], [w for w, _s in words]))
    rnd.shuffle(pool)
    out = []
    for sid, words in pool[:n]:
        k = min(len(words), 3)
        out.append((" ".join(words[:k]), sid))
    return out

def evaluate(ag, rows, usage, now, queries, byid):
    strict = tol = 0; rr = 0.0
    for q, exp in queries:
        ranked = ag.rank_sessions(rows, ag.parse_query(q), usage=usage, now=now)
        sids = [f[ag.C_SID] for _s, _m, f in ranked]
        pos = sids.index(exp) + 1 if exp in sids else None
        ok = bool(sids) and sids[0] == exp
        et = byid[exp][ag.C_TITLE] if exp in byid else None
        strict += ok
        tol += ok or (bool(ranked) and et is not None and ranked[0][2][ag.C_TITLE] == et)
        rr += 1 / pos if pos else 0
    n = len(queries)
    return strict / n, tol / n, rr / n

def main(paths):
    ref = load(paths[0][1], "ag_ref")
    rows = load_snapshot_rows(ref); usage, now = load_snapshot_meta(ref)
    byid = {r[ref.C_SID]: r for r in rows}
    gold = [(g["query"], g["expected_sid"]) for g in load_gold_jsonl(gold_jsonl_path(ref))]
    held = heldout_queries(ref, rows)
    print(f"corpus {len(rows)} sessions · gold {len(gold)} queries · held-out {len(held)} queries\n")
    print(f"{'candidate':22} {'gold@1':>8} {'gold-tol':>9} {'goldMRR':>8} | {'held@1':>8} {'heldMRR':>8} | {'sec/query':>10}")
    for label, path in paths:
        ag = load(path, "ag_" + label.replace(" ", "_").replace("/", "_"))
        g1, gt, gm = evaluate(ag, rows, usage, now, gold, byid)
        t0 = time.perf_counter()
        h1, _ht, hm = evaluate(ag, rows, usage, now, held, byid)
        dt = (time.perf_counter() - t0) / len(held)
        print(f"{label:22} {g1:>8.3f} {gt:>9.3f} {gm:>8.3f} | {h1:>8.3f} {hm:>8.3f} | {dt:>10.4f}")

if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or len(argv) % 2 or "-h" in argv or "--help" in argv:
        raise SystemExit(__doc__)
    main([(argv[i], argv[i + 1]) for i in range(0, len(argv), 2)])
