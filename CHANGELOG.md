# Changelog

All notable changes to agsearch are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

While agsearch is on `0.x`, the CLI surface may still change between minor
versions. Anything that changes it will be listed under **Changed** with the
migration in the same line.

## [Unreleased]

## [0.1.0] - 2026-08-21

The packaging release. agsearch has worked for a while; this is the first
version you can name, install reproducibly, and report a bug against.

### Added

- **MIT license.** The repo was previously unlicensed, which meant "all rights
  reserved" by default and made it ineligible for every package manager.
- **`--version` / `-V`**, backed by a single `__version__` literal that
  packaging reads directly, so the tag, the formula and the CLI cannot drift.
- **Cold-build progress.** The first index over a large corpus takes several
  seconds; it now reports `indexing 412/1238 sessions...` instead of appearing
  to hang. Silent on warm runs and whenever stderr is not a tty, so piped
  output stays clean.
- **Homebrew tap** — `brew install devcodes9/tap/agsearch`, which resolves both
  PATH and the `fzf` dependency in one step.
- **CI** across macOS and Linux on Python 3.9 and 3.13, including a smoke test
  that runs the installer end to end.

### Changed

- **`install.sh` installs the latest tagged release** rather than `main` HEAD.
  Pin with `AGSEARCH_VERSION=v0.1.0`, or take unreleased tip with
  `AGSEARCH_VERSION=main`. Downloads are staged and validated before landing on
  your PATH, so a failed fetch can no longer install a broken script.
- **README** documents the current competitive picture: native `/resume` and
  `codex resume` now search session *metadata*, so the claim is no longer "they
  have no cross-session search" but that they search titles while agsearch
  searches what was said.

### Known limits

- Search is lexical, not semantic: `migration` will not find "porting the
  database". Embeddings are a deliberate future step.
- Claude Code deletes transcripts after 30 days by default
  (`cleanupPeriodDays`). agsearch can only find what is still on disk — see the
  README for how to change it.
- The JSONL schema is Claude Code's internal format and can change between
  releases. Run `agsearch --reindex` after an upgrade if results look wrong.

[Unreleased]: https://github.com/devcodes9/agsearch/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/devcodes9/agsearch/releases/tag/v0.1.0
