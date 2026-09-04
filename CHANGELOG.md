# Changelog

All notable changes to agsearch are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

While agsearch is on `0.x`, the CLI surface may still change between minor
versions. Anything that changes it will be listed under **Changed** with the
migration in the same line.

## [Unreleased]

### Added

- **Forked sessions are marked `fork`** in the list, and the preview and `read` headers
  name the branch they came from and the message they split at. Claude Code forks a
  conversation by copying the transcript into a new file under a new session id and
  records nothing that says so, so the two branches sat in the list as unrelated rows
  with the same title, the same project and the same opening prompt. Picking the wrong
  one resumes a branch missing everything after the split. Detection reads the only
  trace the format leaves: copied messages keep the uuids they had in the original.
  Claude Code sessions only, and it costs one extra partial read per new transcript.

## [0.1.1] - 2026-08-22

Documentation and messaging. No behaviour change.

### Fixed

- **fzf install advice named Homebrew on Linux.** The installer note and the
  runtime fallback both said `brew install fzf`, which is wrong on the platform
  the reader is most likely using. Both now link to fzf's installation page.
- **The fzf version floor was undocumented.** agsearch binds fzf's `start`
  event, added in fzf 0.35.0, so anything older fails with `unknown event:
  start`. Some distributions still package below that.

### Changed

- **The quick start leads with Homebrew**, which also resolves `fzf` so the
  interactive interface works on first run. `uvx` follows, for running a single
  search without installing. 0.1.0 led with `uvx`, which fails for anyone
  without `uv`.
- **README notes that other agents are addable.** Gemini CLI and opencode are
  tracked in #40.

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
- **PyPI** — `uvx agsearch -n "query"` runs the tool with nothing installed.
  Published via Trusted Publishing, so no API token exists in the repo.
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

[Unreleased]: https://github.com/devcodes9/agsearch/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/devcodes9/agsearch/releases/tag/v0.1.1
[0.1.0]: https://github.com/devcodes9/agsearch/releases/tag/v0.1.0
