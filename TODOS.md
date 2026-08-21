# TODOs


## Short/numeric queries like `PR 1144` still rank ~128

- **What:** A query mixing a short acronym with a precise identifier puts the right session around rank 128 even after the word-boundary fix. Decide how identifiers should score.
- **Why:** `1144` appears in 16 sessions and is the whole intent of the query, but BM25 body length-normalization plus the `matched` tiebreaker treat it as one of two equal terms alongside a near-stopword acronym.
- **Pros:** Fixes the single worst class in the gold set; `pull/1144`-style lookups are a real habit.
- **Cons:** Easy to overfit. Any "boost exact identifiers" rule needs to hold on queries that were never tuned on.
- **Context:** Word-boundary counting moves this 137 → 128 only, so it is a separate cause, not the same bug.
- **Depends on / blocked by:** Word-boundary tf landing first.

## Gold labels pin one of several near-identical sessions

- **What:** recall@1 counts a MISS when top-1 is a *different session with the same title* as the label. On the current set that is `northdata` (2 sessions share `compass to northdata migration`). Either accept same-title equivalents or label a set of acceptable sids per query.
- **Why:** Resuming a continued or duplicated session satisfies the user, so the metric currently understates quality: 0.667 strict vs 0.733 same-title-tolerant.
- **Pros:** The number starts tracking the thing being optimized.
- **Cons:** Same-title equivalence is a proxy. `expected_sids` as a list is more honest and more labeling work.
- **Context:** Affects every future ranking delta, so worth settling before the next ranking PR.
- **Depends on / blocked by:** Nothing.
