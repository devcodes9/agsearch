# TODOs

## Commit `_launch_dir`

- **What:** Stash today's uncommitted `_launch_dir` Claude resume patch and commit it (when you 1Password-sign).
- **Why:** Nested Claude project dirs attach wrong without `_launch_dir`.
- **Pros:** Attach trust; the working patch is not discarded.
- **Cons:** Separate PR; not hit quality.
- **Context:** Uncommitted `agsearch` on `main` already implements `_launch_dir`. Close GitHub #10/#12 without merging them. The other half of this item — source-aware, `shlex.quote`d `--no-resume` output — shipped with the TUI UX cut as `resume_command()`.
- **Depends on / blocked by:** Commit only when you explicitly sign.

## Preview card for title, first-prompt, and typo #1s

- **What:** After stem-on-body preview ships, show matches when ranker won via title, first prompt, or `_fuzzy_span`, so `0 match(es)` cannot happen on a #1 row.
- **Why:** This cut only AND-matches ranking keys on message text.
- **Pros:** Preview equals rank.
- **Cons:** Second matching path inside `render_preview`.
- **Context:** `render_preview` (`agsearch:566-577`) currently uses raw `query.split()` on body; this cut switches to `parse_query` keys on body only.
- **Depends on / blocked by:** Stem-on-body preview PR. Frozen gold snapshot so you can list leftover 0-match queries.

## Count term frequency on word boundaries, not substrings

- **What:** `rank_sessions` uses `body_hay.count(key)`, a raw substring count. Switch to a word-prefix count (`\b<key>`), keeping prefix semantics so stems still match their inflections.
- **Why:** `pr` occurs as a substring in 700/718 snapshot sessions but as a word in only 182. It matches inside `previously`, `private`, `promise`, `prisma`. That collapses its idf to near zero and makes the `matched` coverage tiebreaker meaningless, so the discriminative term in the query gets drowned.
- **Pros:** Measured on the frozen snapshot: recall@1 0.667 → 0.733 (`dependent PRs` moves 3 → 1), MRR 0.762 → 0.806. Word-prefix is the standard IR treatment, not a tuned heuristic.
- **Cons:** `re.findall` per key per field is slower than `str.count` on a 718-row corpus. Measure before shipping.
- **Context:** Ranking change, so per the design doc it needs its own PR with a stated @1 delta. Not part of the preview cut.
- **Depends on / blocked by:** Frozen `gold-meta.json`, so the delta is measured against a fixed baseline.

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
