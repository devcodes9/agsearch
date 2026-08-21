# TODOs

## Preview card for title, first-prompt, and typo #1s

- **What:** After stem-on-body preview ships, show matches when ranker won via title, first prompt, or `_fuzzy_span`, so `0 match(es)` cannot happen on a #1 row.
- **Why:** This cut only AND-matches ranking keys on message text.
- **Pros:** Preview equals rank.
- **Cons:** Second matching path inside `render_preview`.
- **Context:** `render_preview` (`agsearch:566-577`) currently uses raw `query.split()` on body; this cut switches to `parse_query` keys on body only.
- **Depends on / blocked by:** Stem-on-body preview PR. Frozen gold snapshot so you can list leftover 0-match queries.

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

## Typo fallback fires on everything when the corpus is small

- **What:** `rank_sessions` treats a term found in <= 2 sessions as a probable typo and falls back to subsequence matching. That threshold is absolute, so on a small corpus every term is "rare" and everything gets fuzzy-matched. Scale it to corpus size instead.
- **Why:** A new user with a handful of sessions gets subsequence noise on their very first search, which is the worst possible first impression for a tool whose pitch is hit quality. Found while writing a two-row test fixture that silently matched everything.
- **Pros:** Precision holds from session one, not just once the corpus is large.
- **Cons:** Needs a rule that behaves at both ends. A fraction of `n` is the obvious move but is untested at either extreme.
- **Context:** Invisible on the 718-session snapshot, so the gold set cannot detect it. Needs its own small-corpus fixtures.
- **Depends on / blocked by:** Nothing.
