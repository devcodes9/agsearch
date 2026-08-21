# TODOs


## Short/numeric queries like `PR 1144` still rank ~128

- **What:** A query mixing a short acronym with a precise identifier puts the right session around rank 128 even after the word-boundary fix. Decide how identifiers should score.
- **Why:** `1144` appears in 16 sessions and is the whole intent of the query, but BM25 body length-normalization plus the `matched` tiebreaker treat it as one of two equal terms alongside a near-stopword acronym.
- **Pros:** Fixes the single worst class in the gold set; `pull/1144`-style lookups are a real habit.
- **Cons:** Easy to overfit. Any "boost exact identifiers" rule needs to hold on queries that were never tuned on.
- **Context:** Word-boundary counting moves this 137 → 128 only, so it is a separate cause, not the same bug.
- **Depends on / blocked by:** Word-boundary tf landing first.

## `--fuzzy` is accepted but never applied

- **What:** `--fuzzy` is parsed, passed to `run_fzf`, and dropped: `cmd_filter` does all the matching and never sees it. Either wire it into `rank_sessions` (loosen the typo tier for every term instead of only near-absent ones) or remove the flag.
- **Why:** README advertises "fuzzy matching instead of the default exact substring". Today the flag changes nothing in the TUI, which is worse than not having it.
- **Pros:** Removes a documented no-op; either outcome is honest.
- **Cons:** Wiring it in is a ranking change, so it needs its own recall@1 delta against the frozen gold set.
- **Context:** Pre-existing; predates the TUI UX cut, which only made the dead plumbing visible by removing the unused argv slot it rode on.
- **Depends on / blocked by:** Frozen `gold-meta.json`, if you wire it rather than remove it.
