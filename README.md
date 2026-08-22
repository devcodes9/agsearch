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
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="license: MIT"></a>
</p>

<!-- Demo GIF goes here once recorded: `brew install vhs && vhs docs/demo.tape` -->

## Why not just `/resume`?

Claude Code's `/resume` picker and `codex resume` both got good recently — `/resume` searches
across every project on the machine, filters by branch and worktree, and previews. If you
remember roughly what a session was *called*, use them. They're free and already installed.

Read what they match on, though. Claude matches "the session name if you set one, otherwise the
AI-generated title, conversation summary, or first prompt." Codex matches name, preview, thread
id, branch, cwd. **Both search metadata about the session. Neither searches inside the
conversation.**

> Native search finds sessions by what they were **called**.
> agsearch finds them by what was **said** in them — ranked, across Claude and Codex.

Three other differences worth knowing:

- **Cross-tool.** One ranked list over Claude *and* Codex. Rows tagged `cc` / `cx`.
- **It actually resumes.** Picking a session from an unrelated project in the native picker
  copies a `cd`+resume command to your clipboard. agsearch resumes it.
- **It sees `-p` / SDK sessions.** Those never appear in the native picker at all. agsearch
  indexes them, dimmed and tagged `auto`.

## Try it without installing anything

```sh
uvx agsearch -n "stripe tax id"
```

That searches your real sessions and prints ranked matches. Nothing is installed, nothing is
left behind. agsearch is stdlib-only, so there is nothing to compile either.

## Install

```sh
brew install devcodes9/tap/agsearch
```

Brew is the recommended path because it resolves `fzf` and your PATH in the same step, and
`fzf` is what the interactive TUI needs. `uvx` cannot install it, because fzf is not a Python
package — that is the one thing the zero-install route above cannot give you.

Otherwise:

```sh
curl -fsSL https://raw.githubusercontent.com/devcodes9/agsearch/main/install.sh | sh
```

Installs the latest release to `~/.local/bin`. Override with `PREFIX=` or pin with
`AGSEARCH_VERSION=v0.1.0`.

Requirements: **Python 3**, no packages. **[`fzf`](https://github.com/junegunn/fzf)** for the
interactive TUI — `agsearch -n "query"` works without it.

> [!IMPORTANT]
> **Claude Code deletes transcripts after 30 days by default.** agsearch can only find what is
> still on disk, and the default `cleanupPeriodDays: 30` means your history is quietly
> evaporating right now. If you want a searchable archive, raise it in `~/.claude/settings.json`:
>
> ```json
> { "cleanupPeriodDays": 365 }
> ```
>
> This is your setting to change — agsearch never writes to it.

## Use

```sh
agsearch                     # interactive TUI: one row per session, over all sessions
agsearch "stripe tax id"     # TUI pre-filtered to a query
agsearch --fuzzy "..."       # fuzzy matching instead of the default exact substring
agsearch -n "stripe tax id"  # non-interactive: print ranked matches (no fzf)
agsearch --here "..."        # only sessions from the current directory's project
agsearch --project myapp     # only sessions whose path contains 'myapp'
agsearch --thinking          # also search assistant thinking blocks
agsearch --reindex           # force a full cache rebuild
agsearch --version           # print the installed version
```

**Enter** resumes the session (cd's to its project dir, runs `claude --resume`), **Ctrl-/**
toggles the preview. **Ctrl-o** opens the whole conversation in your pager — no resume, no CLI
start, no tokens spent — which is usually all you needed to check you had the right session.
**Ctrl-y** copies the reattach command. Add `--no-resume` to print it instead.

Search is **exact substring, AND-of-terms** by default (`stripe webhook` = both words). Operators
work in either mode: `'word` force-exact, `^prefix`, `suffix$`, `!exclude`, `a | b` for OR. Pass
`--fuzzy` for typo-tolerant matching.

[Optional: bind it to a global hotkey](docs/hotkey.md) — Raycast, Hammerspoon or skhd. Not
required; if you're running `claude` you're already at a prompt.

## Runs fully local

Your sessions are indexed and searched on your machine — nothing is uploaded, and agsearch makes
no network calls at all. It reads the JSONL your agent CLIs already wrote, caches the index under
`~/.cache/agsearch/`, and the only programs it ever shells out to are `fzf`, a clipboard tool
(`pbcopy`, `wl-copy`, `xclip` or `xsel`, whichever you have), and the `claude`/`codex` CLI you
asked it to resume.

No Elasticsearch needed: it's ripgrep-speed over local JSONL with a per-file cache. Cold build
over ~1,200 sessions is a few seconds (it tells you how far along it is); every warm search after
that is ~0.1s.

## What the results look like

The TUI lists **one clean row per session**: `date · project · N/T · title`, where `N/T` is how many
of your query terms the session matched. Search runs over the full conversation text (agsearch does
the matching itself and feeds fzf only matching sessions, so the list stays clean while every word is
searchable). The right pane is a **compact preview card**, not a transcript dump: with a query it
shows only the matched lines (highlighted); with no query, the bookends (first prompt + last message)
so you know what the session was about. Full reading is what **resume** is for.

**Snippets are cleaned, not raw.** Transcripts are full of things nobody wants to read in a result
row, so every snippet strips markdown noise (fences, headings, bullets, emphasis, link syntax) and
condenses payloads — JSON dumps, `cat -n` file reads, pasted images, long opaque tokens — into short
`[json]` / `[file]` / `[image]` placeholders, on one fixed-width line. Search still runs over the
raw text, and if your term only exists inside a condensed payload the raw line is shown instead:
a snippet always contains the word you searched for, highlighted.

**Sessions are categorised, not filtered.** Claude Code records how each session started
(`entrypoint`): `cli` = you typed it, `sdk-py`/`sdk-ts` = spawned by a plugin or SDK process
(e.g. the security-guidance plugin's Stop hook, which opens a fresh session per git diff). Your
own sessions always rank **above** automation; automated runs still appear, dimmed and tagged
`auto`, so nothing is hidden. Row markers: `cc` Claude, `cx` Codex, `auto` plugin/SDK run.

**Subagents fold into their parent.** `agent-*` subagent transcripts (Explore/Task/guide agents)
can't be resumed on their own, so their content is searched as part of the **parent conversation
that spawned them** (linked via the subagent's `sessionId` field). A hit in subagent text lists
and resumes the parent; the preview shows subagent lines tagged `⤷`. So the list stays at ~325
real sessions while nothing is lost from search.

Resume is **id-based**, so a session whose project dir has since been deleted (a removed worktree)
still resumes — agsearch cd's to the nearest surviving ancestor of the dead path (or `$HOME`) and
prints a one-line notice. Those rows carry a dim `orig dir gone` tag in the list, and the preview
card says so too; it's a footnote, not a gate — the session opens exactly like any other. Sessions
written to in the last few minutes are probably still running: they're marked **●**, and Enter
warns (and asks, when there's a tty) before attaching.

Because Claude Code renders its own TUI, an outside tool can't highlight a line *inside* the
resumed session. So the highlighted-in-context view lives in the preview pane (before you spend
any tokens), and as a bonus, Enter copies your query to the clipboard: once the session reopens,
press **⌘F → ⌘V → Enter** to jump to the match in whatever iTerm holds in scrollback.

## How ranking works

Search is **BM25 ranked**, not just substring. It drops stopwords, applies a conservative stem so
`migration`≈`migrate`≈`migrating`, and scores each session over three weighted fields — title +
project, the session's **first prompt**, and the full transcript. The first prompt is what you
opened the session *asking for*, so it's weighted hardest; **length normalization** means a
sprawling transcript that mentions your term once no longer outranks a short, on-point session.
Near-ties are then nudged by **recency** and by how often you've actually resumed that session
(read off agsearch's own resume log). Badge `N/T` = query terms matched. A word that barely exists
anywhere (a typo like `alibrry`) falls back to subsequence matching. No modes or flags.

**Honest limit:** this is lexical, not semantic. Ranking beats an unordered `rg` dump, but it
is not a guarantee that row one is the session you meant. Because transcripts are large,
lower-ranked results can share a badge while being only loosely related, and it won't match by
*meaning* (e.g. `migration` won't find "porting the database"). That needs embeddings, a
deliberate future step, not more matching heuristics.

## How it works

- Walks `~/.claude/projects/**/*.jsonl` and `~/.codex/sessions/**/*.jsonl`, extracting user
  prompts and assistant text (one row per message) plus each session's AI-generated title.
  A source-adapter layer means new agents (Cursor, Gemini, …) are just another parser.
- Caches parsed output per file, keyed by mtime, under `~/.cache/agsearch/`. Only changed
  sessions are re-parsed on later runs.
- The JSONL schema is Claude Code's internal format and can change between releases; if a
  future version breaks parsing, run `agsearch --reindex` after updating.
- Ranking is covered by tests over a small fixture corpus (no dependencies, no fixtures on
  disk): `python3 -m unittest discover -s tests`.

## Contributing

MIT licensed. Changes to ranking should come with a case in `tests/` — the gold-set scorer is
how we keep recall@1 from regressing. See [CHANGELOG.md](CHANGELOG.md) for what shipped when.
