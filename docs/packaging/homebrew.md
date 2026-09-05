# Homebrew

`brew install devcodes9/tap/agsearch` is the install path that removes the most
friction, because it resolves the two things the `curl | sh` route cannot:

- **PATH.** No "add `~/.local/bin` to your shell profile, then restart your
  shell" step.
- **`fzf`.** Today the installer can only *warn* that fzf is missing, and the
  user finds out after installing. `depends_on "fzf"` makes it brew's problem.

That takes the install ladder from six steps to one.

## Why a tap and not homebrew-core

Homebrew's notability thresholds are hardcoded in `shared_audits.rb`:

| Route | Forks | Watchers | Stars | Repo age |
|---|---|---|---|---|
| Third party submits your formula | 30 | 30 | 75 | ≥30 days |
| **You submit your own repo** | **90** | **90** | **225** | ≥30 days |

agsearch is at 0 / 0 / 0. Core is not close, and self-submission has the
strictest bar of the two.

In a **tap**, none of it applies — the entire notability, fork and age audit is
gated behind `return unless @core_tap`, so it simply does not run. Migrating to
core later, if the numbers ever get there, is close to a one-line diff.

The tradeoff, stated plainly: a tap is a second repo to maintain and a sha256 to
bump on every release. `bump-tap.yml` in this repo automates the bump; the
second repo is real but small.

One thing to know: nobody in the well-packaged-CLI reference set publishes a
personal tap from CI — they are all in homebrew-core. A tap is the right call
here, but it is off the beaten path, so expect fewer worked examples.

## One-time setup

```sh
brew tap-new devcodes9/tap          # scaffolds the repo, incl. a daily autobump
cd "$(brew --repository)/Library/Taps/devcodes9/homebrew-tap"
mkdir -p Formula
cp /path/to/agsearch/packaging/agsearch.rb Formula/agsearch.rb
```

Then fill in the real `sha256` for the tagged tarball:

```sh
curl -fsSL https://github.com/devcodes9/agsearch/archive/refs/tags/v0.1.0.tar.gz \
  | shasum -a 256
```

Verify before pushing — `brew test` is what catches the sandbox traps the
formula's comments describe:

```sh
brew install --build-from-source devcodes9/tap/agsearch
brew test agsearch
brew audit --strict --online devcodes9/tap/agsearch
```

Push the tap repo to `github.com/devcodes9/homebrew-tap`. The `homebrew-` prefix
is what makes `devcodes9/tap` resolve.

## Releases after the first

`packaging/agsearch.rb` in this repo is the source of truth; the tap holds a
copy at `Formula/agsearch.rb`.

`.github/workflows/bump-tap.yml` runs when a release is published and opens the
version + sha256 bump against the tap automatically. It needs one secret:

- **`HOMEBREW_TAP_TOKEN`** — a fine-grained PAT with `contents: write` on
  `devcodes9/homebrew-tap` only.

Without that secret the job logs a notice and skips. Cutting a release never
blocks on tap plumbing; you just bump the formula by hand until it is set up.

## The test block

Homebrew's cookbook explicitly calls a `--version`-only test insufficient, so
the formula writes a fixture session under `testpath` and asserts that a real
query finds it. Three traps it works around, all verified against the real
parser rather than assumed:

1. **`HOME` must be redirected into `testpath`** or the sandbox blocks the cache
   write.
2. **An empty `HOME` exits 1** with "No indexed sessions found", so the fixture
   has to exist before agsearch runs.
3. **`-n` emits ANSI highlighting even when piped**, so the query string is not
   a contiguous substring of the output. The assertions use unhighlighted text
   (`billing/config.py`) instead.

## Why v0.2.0 shipped with a stale formula

Two faults, both now fixed in the workflow:

- It triggered on `release: published`. The release is created by the release
  workflow using `GITHUB_TOKEN`, and GitHub does not start workflows from
  `GITHUB_TOKEN` events, so the job never ran. It triggers on the `v*` tag now,
  the same as `release` and `publish-pypi`.
- `HOMEBREW_TAP_TOKEN` is still not set, so a manual dispatch skipped rather than
  bumped. Until that secret exists, a release needs the formula updated by hand:
  point `url` at the new tag and replace `sha256` with
  `shasum -a 256` of that tarball.
