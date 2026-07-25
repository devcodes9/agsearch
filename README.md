# agsearch

Global search across every **Claude Code** and **OpenAI Codex CLI** session, then resume the
one you want, in whichever tool it came from.

Each agent stores sessions as local JSONL (Claude under `~/.claude/projects/`, Codex under
`~/.codex/sessions/`) but neither has cross-session search. `agsearch` indexes them all into one
smart-ranked search, previews the matching lines, and drops you back in with `claude --resume`
or `codex resume` as appropriate. Rows are tagged `cc` (Claude) or `cx` (Codex). A source-adapter
layer means new agents (Cursor, Gemini, …) are just another parser.

No Elasticsearch needed: it's ripgrep-speed over local JSONL with a per-file cache. Cold build
over ~1,200 sessions is a few seconds; every warm search after that is ~0.1s.

**Runs fully local.** Your sessions are indexed and searched on your machine — nothing is
uploaded, and agsearch makes no network calls at all. It reads the JSONL your agent CLIs already
wrote, caches the index under `~/.cache/agsearch/`, and the only programs it ever shells out to
are `fzf`, `pbcopy`, and the `claude`/`codex` CLI you asked it to resume.

## Install

One line (installs to `~/.local/bin`, override with `PREFIX=`):

```sh
curl -fsSL https://raw.githubusercontent.com/devcodes9/agsearch/main/install.sh | sh
```

Or from a clone:

```sh
git clone https://github.com/devcodes9/agsearch && cd agsearch && ./install.sh
```

Requirements: **Python 3** (no packages needed) and **[`fzf`](https://github.com/junegunn/fzf)**
for the interactive TUI (`brew install fzf`). The non-interactive mode (`agsearch -n "query"`)
works without fzf.

### Optional: global hotkey

Bind it to a system-wide shortcut so search is always one keypress away. With
[Hammerspoon](https://www.hammerspoon.org), this pops a floating terminal that *becomes* your
resumed session on Enter:

```lua
hs.hotkey.bind({ "ctrl", "cmd" }, "k", function()
  hs.osascript.applescript([[
    tell application "iTerm"
      activate
      create window with default profile command "/bin/zsh -lic \"exec agsearch\""
    end tell]])
end)
```

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
```

The TUI lists **one clean row per session**: `date · project · N/T · title`, where `N/T` is how many
of your query terms the session matched. Search runs over the full conversation text (agsearch does
the matching itself and feeds fzf only matching sessions, so the list stays clean while every word is
searchable). The right pane is a **compact preview card**, not a transcript dump: with a query it
shows only the matched lines (highlighted); with no query, the bookends (first prompt + last message)
so you know what the session was about. Full reading is what **resume** is for.

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

Search is **BM25 ranked**, not just substring. It drops stopwords, applies a conservative stem so
`migration`≈`migrate`≈`migrating`, and scores each session over three weighted fields — title +
project, the session's **first prompt**, and the full transcript. The first prompt is what you
opened the session *asking for*, so it's weighted hardest; **length normalization** means a
sprawling transcript that mentions your term once no longer outranks a short, on-point session.
Near-ties are then nudged by **recency** and by how often you've actually resumed that session
(read off agsearch's own resume log). Badge `N/T` = query terms matched. A word that barely exists
anywhere (a typo like `alibrry`) falls back to subsequence matching. No modes or flags.

Honest limit: this is lexical, not semantic. The top hit is reliably right, but because
transcripts are large, lower-ranked results can share a badge while being only loosely related,
and it won't match by *meaning* (e.g. `migration` won't find "porting the database"). That needs
embeddings, a deliberate future step, not more matching heuristics.

Search is **exact substring, AND-of-terms** by default (`stripe webhook` = both words). Operators
work in either mode: `'word` force-exact, `^prefix`, `suffix$`, `!exclude`, `a | b` for OR. Pass
`--fuzzy` for typo-tolerant matching.

**Enter** resumes the session (cd's to its project dir, runs `claude --resume`), **Ctrl-/** toggles
the preview. Add `--no-resume` to print the resume command instead.

Resume is **id-based**, so a session whose project dir has since been deleted (a removed worktree)
still resumes — agsearch cd's to the nearest surviving ancestor of the dead path (or `$HOME`) and
prints a one-line notice. Sessions written to in the last few minutes are probably still running:
they're marked **●** in the list, and Enter warns (and asks, when there's a tty) before attaching.

Because Claude Code renders its own TUI, an outside tool can't highlight a line *inside* the
resumed session. So the highlighted-in-context view lives in the preview pane (before you spend
any tokens), and as a bonus, Enter copies your query to the clipboard: once the session reopens,
press **⌘F → ⌘V → Enter** to jump to the match in whatever iTerm holds in scrollback.

## How it works

- Walks `~/.claude/projects/**/*.jsonl`, extracting user prompts and assistant text (one row
  per message) plus each session's AI-generated title.
- Caches parsed output per file, keyed by mtime, under `~/.cache/agsearch/`. Only changed
  sessions are re-parsed on later runs.
- The JSONL schema is Claude Code's internal format and can change between releases; if a
  future version breaks parsing, run `agsearch --reindex` after updating the extractor.
- Ranking is covered by tests over a small fixture corpus (no dependencies, no fixtures on
  disk): `python3 -m unittest discover -s tests`.
