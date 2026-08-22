<h1 align="center">agsearch</h1>

<p align="center">
  <strong>Find the session you remember,<br>
  even when you don't remember its title.</strong>
</p>

<p align="center">
  Ranked full-text search across every <strong>Claude Code</strong> and
  <strong>Codex CLI</strong> session on your machine.
</p>

<p align="center">
  <a href="https://github.com/devcodes9/agsearch/actions/workflows/ci.yml"><img src="https://github.com/devcodes9/agsearch/actions/workflows/ci.yml/badge.svg" alt="ci"></a>
  <a href="https://github.com/devcodes9/agsearch/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="license: MIT"></a>
</p>

agsearch indexes the local transcripts your coding agents already write. Search them in one
ranked list, preview the matching lines, and resume the original Claude Code or Codex session.
Everything stays on your machine.

<!-- Demo GIF goes here once recorded: `brew install vhs && vhs docs/demo.tape` -->

## Quick start

Try a search without installing anything:

```sh
uvx agsearch -n "stripe tax id"
```

For the interactive interface:

```sh
brew install devcodes9/tap/agsearch
agsearch
```

Type anything you remember from a past conversation. Select a result to resume it.

## Features

- **Full-conversation search.** Search user prompts and assistant replies, not only titles and
  session metadata.
- **One list for both tools.** Claude Code and Codex sessions appear together, labelled `cc`
  and `cx`.
- **Ranked results.** BM25 ranking favors focused sessions and shows matching lines in context.
- **Preview, read, or resume.** Inspect a match, open the transcript in a pager, or return to the
  original session.
- **Fully local.** No uploads, API keys, hosted index, or network calls.
- **Fast warm searches.** A per-file cache reparses only transcripts that changed.

## Installation

### Homebrew

Recommended because it installs both agsearch and the `fzf` dependency:

```sh
brew install devcodes9/tap/agsearch
```

### Python tool installers

```sh
uv tool install agsearch
# or
pipx install agsearch
```

Install [`fzf`](https://github.com/junegunn/fzf) separately for the interactive interface.
Without it, `agsearch -n "query"` still works.

### Install script

```sh
curl -fsSL https://raw.githubusercontent.com/devcodes9/agsearch/main/install.sh | sh
```

This installs the latest release to `~/.local/bin`. Set `PREFIX` to change the destination or
`AGSEARCH_VERSION` to pin a release.

agsearch requires Python 3.9 or newer and has no Python package dependencies.

## Usage

```sh
agsearch                       # browse all sessions in the interactive interface
agsearch "stripe tax id"       # open with an initial query
agsearch -n "stripe tax id"    # print ranked matches without fzf
agsearch --here "webhook"      # search only the current project
agsearch -p myapp "migration"  # search projects whose path contains "myapp"
agsearch --thinking "query"    # include assistant thinking blocks
agsearch --no-resume "query"   # print the selected resume command
agsearch --reindex             # rebuild the transcript cache
agsearch --version             # print the installed version
```

### Interactive keys

| Key | Action |
| --- | --- |
| <kbd>Enter</kbd> | Resume the selected session |
| <kbd>Ctrl-O</kbd> | Read the full conversation in your pager |
| <kbd>Ctrl-Y</kbd> | Copy the resume command |
| <kbd>Ctrl-/</kbd> | Toggle the preview pane |

Selecting a result starts `claude --resume` or `codex resume` from the session's project
directory. The current query is copied to the clipboard so you can find the same text after
resuming.

For a global shortcut, see the
[hotkey guide](https://github.com/devcodes9/agsearch/blob/main/docs/hotkey.md).

## Why not just `/resume`?

Claude Code's `/resume` picker and `codex resume` are good when you remember a session's title,
branch, directory, or first prompt. They search metadata about the session.

agsearch searches the conversation itself. It also combines both tools in one list and includes
Claude Code SDK and `-p` sessions that do not appear in the native picker.

Use the native picker when you remember what the session was called. Use agsearch when you
remember what was said.

## Search and ranking

agsearch drops common stopwords, applies conservative stemming, and ranks matching sessions with
BM25 across three weighted fields: title and project, first prompt, and full transcript. Sessions
covering more query terms rank first; relevance, recency, and previous resumes break close ties.
Rare long typos can fall back to subsequence matching.

Search is lexical, not semantic. It will not match concepts expressed with completely different
words, and the first result is not guaranteed to be the session you intended.

## Privacy and storage

agsearch reads:

- `~/.claude/projects/**/*.jsonl`
- `~/.codex/sessions/**/*.jsonl`

Its cache lives under `~/.cache/agsearch/`. Transcript parsing and ranking happen locally, and
only changed files are reparsed.

> [!IMPORTANT]
> Claude Code deletes transcripts after 30 days by default. To keep a longer searchable history,
> set `cleanupPeriodDays` in `~/.claude/settings.json`:
>
> ```json
> { "cleanupPeriodDays": 365 }
> ```
>
> agsearch never changes this setting.

## Session handling

- Claude Code subagent transcripts are folded into their resumable parent session.
- SDK and other automated sessions remain searchable but rank below user-started sessions.
- Sessions from deleted worktrees resume from the nearest existing parent directory.
- Recently active sessions are marked `●` and require confirmation before reattaching.

## Development

```sh
git clone https://github.com/devcodes9/agsearch.git
cd agsearch
python3 -m unittest discover -s tests
```

Changes to ranking should include a regression case in `tests/`. See the
[changelog](https://github.com/devcodes9/agsearch/blob/main/CHANGELOG.md) and
[open issues](https://github.com/devcodes9/agsearch/issues).

## License

[MIT](https://github.com/devcodes9/agsearch/blob/main/LICENSE)
