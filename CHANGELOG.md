# Changelog

All notable changes to agsearch are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

While agsearch is on `0.x`, the CLI surface may still change between minor
versions. Anything that changes it will be listed under **Changed** with the
migration in the same line.

## [Unreleased]

### Added

- **Cursor, opencode and Gemini CLI sessions are indexed, searched and resumed** alongside
  Claude Code and Codex, labelled `cu`, `oc` and `gm`. Cursor keeps each chat as a SQLite store under
  `~/.cursor/chats/`, opened read-only, reading message records and skipping the binary and
  image blobs beside them; it resumes with `cursor-agent --resume <id>`. Gemini keeps one JSON
  object per session under `~/.gemini/tmp/`, and resumes with `gemini --session-file <path>`
  because its `--resume` takes a project-scoped index number rather than a stable id.
  opencode keeps every session in one database, so it also resumes by id
  (`opencode --session <id>`) but is read as a whole.
  On a 852-session corpus, adding 101 Cursor sessions moved held-out ranking by +0.004, so
  existing searches are unaffected.
- **A transcript file may now hold more than one session.** The indexer took the first row's
  id as the id for the entire file, which is right for a file per session and wrong for a
  harness that keeps them all in one database: every session but the first was unreachable.
  It now registers each session a file contains, and reading one filters to it. No change for
  Claude Code, Codex, Cursor or Gemini, which write one session per file.

### Changed

- **Harnesses are described by one source table instead of a ternary in five places.** Adding
  an agent was supposed to be one line, but the file extension, the parser used for preview,
  the row label, the preview label and the resume command each decided for themselves what a
  source was, and two of them had already drifted (`codex` against `cx`). They now read one
  record per harness, so a new agent is a parser plus one entry. Behaviour for Claude Code and
  Codex is unchanged; the cache format bumps to 7 and reindexes once on first run.

- **Piped output is shaped for the program reading it.** `-n` and `read` are what a coding
  agent sees, and an agent pays per character for what a terminal gets free. Behind the same
  not-a-terminal test the colour seam already uses: session ids shorten to the shortest prefix
  that still tells every indexed session apart (git's rule, floored at 12 because Codex writes
  time-ordered uuidv7 and 8 characters collide), column padding is dropped, and the output ends
  by naming `agsearch read`. A 20-result search goes from 5748 to 5111 bytes, and further in
  tokens. `read` accepts any unambiguous id prefix and reports how many sessions an ambiguous
  one matched. A terminal sees exactly what it saw before.
- **A piped `read` caps at 12k characters**, keeping the opening turns and as many closing ones
  as fit, because a session is read to learn what the work was and where it stopped. The
  elision names what it dropped and how to get it. `--full`, and any terminal, is uncapped.

- **`-n` now runs the same ranker as the interactive list.** It was a separate path: an
  AND of raw substrings over *message* rows, sorted by date. That meant no BM25, no
  stemming, no typo tier, no demotion of SDK-spawned runs, and one session repeated once
  per matching message. `-n` is also the README's zero-install first command and the
  fallback when fzf is missing, so the surface most new users met was the unranked one.
  It now returns ranked sessions, one entry each. Output shape changed with it: the
  session id leads the line, and the matching text sits indented below it. Cost of the
  shared path is ~0.7s per `-n` run against a 400-session corpus, up from ~0.25s,
  because it builds the same per-session index the list uses.

### Added

- **A Claude Code skill**, installed as a plugin (`/plugin marketplace add devcodes9/agsearch`,
  then `/plugin install agsearch@agsearch`) or by copying `skills/agsearch/` into
  `~/.claude/skills/`. With it Claude searches your transcripts itself when you refer to
  earlier work, rather than answering that it has no record of the conversation, and it can
  carry an old session's context forward into the session you are in now, which resuming
  cannot do. The skill teaches query construction because that is where an agent fails: on a
  247-query benchmark, content words alone rank the right session first 49% of the time, and
  the same words left inside the question that carried them score 10% to 22%.

- **`agsearch read <session-id>`** prints a whole conversation without resuming it. This
  was already there as the TUI's <kbd>Ctrl-O</kbd>, reachable only as an internal
  subcommand; it is now a documented command, so a search hit can actually be opened.
- **Colour only when a terminal is reading.** `-n` and `read` emit plain text when stdout
  is a pipe, or when `NO_COLOR` is set. Escape sequences quoted inside a transcript are
  stripped too, including ones the snippet cut in half.
- **Forked sessions are marked `fork`** ahead of the title, in the list and in the preview
  and `read` headers alike, and those headers also name the branch a fork came from and
  the message the two split at. Claude Code forks a
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
