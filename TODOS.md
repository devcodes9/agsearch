# TODOs

## Source-aware quoted `--no-resume` and commit `_launch_dir`

- **What:** Stash today's uncommitted `_launch_dir` Claude resume patch. After the ranking cut, commit it (when you 1Password-sign) and make `--no-resume` print `codex resume` vs `claude --resume` with `shlex.quote` on `cd`.
- **Why:** Nested Claude project dirs attach wrong without `_launch_dir`. `--no-resume` always prints `cd {cwd} && claude --resume {sid}` (`agsearch:1030-1031`).
- **Pros:** Attach trust; the working patch is not discarded.
- **Cons:** Separate PR; not hit quality.
- **Context:** Uncommitted `agsearch` on `main` already implements `_launch_dir`. Close GitHub #10/#12 without merging them. Do not mix this into the ranking PR.
- **Depends on / blocked by:** `git stash push -m launch-dir agsearch` before merging #13. Commit only when you explicitly sign.

## Cross-platform clipboard for query handoff

- **What:** Replace the hardcoded `pbcopy` call with a best-effort helper that tries `pbcopy`, `wl-copy`, `xclip -selection clipboard`, then `xsel --clipboard --input`, gated on `shutil.which`.
- **Why:** `resume()` (`agsearch:643`) is macOS-only, so the ⌘F query handoff silently does nothing on Linux. README line 18 lists `pbcopy` as a dependency, so this is a stated limit, not a bug, but it is the cheapest portability win available.
- **Pros:** ~15 lines, no ranking overlap, `shutil` is already imported, and injecting `which`/`run` makes it testable.
- **Cons:** Four spawn attempts on a machine with none of them installed.
- **Context:** Salvaged from closed GitHub #12; nothing else from that PR is wanted.
- **Depends on / blocked by:** Nothing.

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
