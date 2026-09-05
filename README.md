<h1 align="center">agsearch</h1>

<p align="center">
  <strong>Find the session you remember,<br>
  even when you don't remember its title.</strong>
</p>

<p align="center">
  Ranked full-text search across the coding-agent sessions already on your machine.<br>
  <strong>Claude Code</strong>, <strong>Codex</strong>, <strong>Cursor CLI</strong>, <strong>opencode</strong> and <strong>Gemini CLI</strong>.
</p>

<p align="center">
  <a href="https://github.com/devcodes9/agsearch/actions/workflows/ci.yml"><img src="https://github.com/devcodes9/agsearch/actions/workflows/ci.yml/badge.svg" alt="ci"></a>
  <a href="https://github.com/devcodes9/agsearch/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="license: MIT"></a>
</p>

agsearch indexes the local transcripts your coding agents already write. Search them in one
ranked list, preview the matching lines, and resume the original session in the tool it came
from. Everything stays on your machine.

<p align="center"><img src="https://raw.githubusercontent.com/devcodes9/agsearch/main/docs/demo.gif" alt="Searching 53 sessions across five coding agents; the second query is misspelled and still lands on the right one" width="100%"></p>

## Quick start

```sh
brew install devcodes9/tap/agsearch
agsearch
```

Type anything you remember from a past conversation. Select a result to resume it.

Homebrew also installs `fzf`, which the interactive interface needs.

To run one search without installing anything:

```sh
uvx agsearch -n "stripe tax id"
```

And inside Claude Code, so Claude searches your past sessions itself rather than telling you
it has no record of them:

```
/plugin marketplace add devcodes9/agsearch
/plugin install agsearch@agsearch
```

[What that changes](#let-claude-search-for-you).

## Features

- **Full-conversation search.** Search user prompts and assistant replies, not only titles and
  session metadata.
- **One list for every tool.** Sessions from all five agents appear together, each row named
  after the tool it came from. Adding another agent is a parser plus one entry in the source
  table, with no change to search or ranking.
- **Ranked results.** BM25 ranking favors focused sessions and shows matching lines in context.
- **Preview, read, or resume.** Inspect a match, open the transcript in a pager, or return to the
  original session.
- **Your agent can search too.** A Claude Code skill, so Claude finds the earlier conversation
  itself instead of answering that it has no record of it.
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

The interactive interface needs [`fzf`](https://github.com/junegunn/fzf#installation) **0.35 or
newer** — that is the release which added the `start` event agsearch binds. Some distributions
package an older one; `fzf`'s own install script is the fallback. Without fzf,
`agsearch -n "query"` still prints ranked sessions.

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
agsearch -n "stripe tax id"    # print ranked sessions as plain text, no fzf
agsearch read <session-id>     # print a whole session, without resuming it
agsearch --here "webhook"      # search only the current project
agsearch -p myapp "migration"  # search projects whose path contains "myapp"
agsearch --thinking "query"    # include assistant thinking blocks
agsearch --no-resume "query"   # print the selected resume command
agsearch --reindex             # rebuild the transcript cache
agsearch --version             # print the installed version
```

### Scripts and coding agents

`-n` prints one entry per session as plain text, led by the session id, and drops colour
whenever it is not writing to a terminal. That makes the search loop scriptable:

```sh
agsearch -n "webhook retry backoff"        # ranked sessions, one entry each
agsearch read 3f2a1c4e-...                 # the whole conversation, no resume, no tokens
```

Ranking is the same as the interactive list, so a term you half-remember or mistype finds
the same session either way. Piped, the session ids shorten to a unique prefix, the columns
lose their padding, and `read` prints the start and end of a long session rather than all of
it. A terminal sees none of that.

### Let Claude search for you

agsearch ships a Claude Code skill. Install it from inside Claude Code:

```
/plugin marketplace add devcodes9/agsearch
/plugin install agsearch@agsearch
```

From the next session on, Claude searches your transcripts itself when you refer to work from
an earlier conversation:

> **you:** what did we decide about the webhook retry backoff?
>
> **Claude:** *runs `agsearch -n "webhook retry backoff"`, reads the top hit, answers from it*

It also covers handoff, which resuming cannot do. `claude --resume` moves you back into the old
session in its own directory; the skill carries that session's context forward into the one you
are in now, so you can pick the work up in a different repository or on a different branch.

The skill is [a single markdown file](https://github.com/devcodes9/agsearch/blob/main/skills/agsearch/SKILL.md).
Read it before installing. If you would rather not add a marketplace, copy it instead:

```sh
mkdir -p ~/.claude/skills && cp -r skills/agsearch ~/.claude/skills/
```

Either way it needs the `agsearch` binary, which the installation section above covers.

### Interactive keys

| Key | Action |
| --- | --- |
| <kbd>Enter</kbd> | Resume the selected session |
| <kbd>Ctrl-O</kbd> | Read the full conversation in your pager |
| <kbd>Ctrl-Y</kbd> | Copy the resume command |
| <kbd>Ctrl-/</kbd> | Toggle the preview pane |

Selecting a result resumes the session in the tool that created it, from that session's
project directory. The current query is copied to the clipboard so you can find the same text after
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
Rare long typos fall back to subsequence matching, so `conection pool` still finds the
session about connection pools.

Search is lexical, not semantic. It will not match concepts expressed with completely different
words, and the first result is not guaranteed to be the session you intended.

## Privacy and storage

agsearch reads:

| Agent | Read from | Resumed with |
| --- | --- | --- |
| Claude Code | `~/.claude/projects/**/*.jsonl` | `claude --resume <id>` |
| Codex | `~/.codex/sessions/**/*.jsonl` | `codex resume <id>` |
| cursor-cli | `~/.cursor/projects/**/agent-transcripts/` | `cursor-agent --resume <id>` |
| opencode | `~/.local/share/opencode/opencode.db` | `opencode --session <id>` |
| Gemini CLI | `~/.gemini/tmp/**/chats/*.json` | `gemini --session-file <path>` |

opencode keeps sessions in SQLite; agsearch opens it read-only and reads message records
only. Gemini's `--resume` takes a project-scoped index number rather than a stable id, so
resume goes through the transcript file instead.

Cursor and Gemini are read from their CLI's storage. Chats made in the Cursor IDE are kept
elsewhere and are not indexed, which is why the column names the CLI.

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
- Forked Claude Code sessions are marked `fork`, and name the branch they split from.

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
