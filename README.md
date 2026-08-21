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
are `fzf`, your clipboard tool (`pbcopy` / `wl-copy` / `xclip` / `xsel`), your pager, and the
`claude`/`codex` CLI you asked it to resume.

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

Bind it to a system-wide shortcut so search is always one keypress away. `--new-tab` opens
agsearch in a **new tab of the terminal you already have open** — that tab then *becomes* your
resumed session on Enter, instead of leaving a stray window behind on every search:

```lua
hs.hotkey.bind({ "ctrl", "cmd" }, "k", function()
  hs.task.new("/Users/you/.local/bin/agsearch", nil, { "--new-tab" }):start()
end)
```

`--new-tab` knows tmux, kitty, WezTerm, iTerm2, Terminal.app, GNOME Terminal, Konsole and
xfce4-terminal, preferring whatever you're currently inside. Force one with
`AGSEARCH_TERMINAL=kitty`, or script an unsupported terminal yourself with
`AGSEARCH_TERMINAL_CMD='myterm -e {cmd}'`.

## Use

```sh
agsearch                     # interactive TUI: one row per session, over all sessions
agsearch "stripe tax id"     # TUI pre-filtered to a query
agsearch --fuzzy "..."       # fuzzy matching instead of the default exact substring
agsearch -n "stripe tax id"  # non-interactive: print ranked matches (no fzf)
agsearch --here "..."        # start scoped to this directory's project (`ctrl-s` widens)
agsearch --project myapp     # only sessions whose path contains 'myapp'
agsearch --thinking          # also search assistant thinking blocks
agsearch --new-tab           # open agsearch in a new tab of this terminal
agsearch --reindex           # force a full cache rebuild
```

The TUI lists **one clean row per session**: `age · project · N/T · title`, where `N/T` is how many
of your query terms the session matched. Search runs over the full conversation text (agsearch does
the matching itself and feeds fzf only matching sessions, so the list stays clean while every word is
searchable). The right pane is a **compact preview card**, not a transcript dump: with a query it
shows only the matched lines (highlighted); with no query, the bookends (first prompt + last message)
so you know what the session was about, plus the exact command Enter is about to run. Full
reading is `ctrl-o`.

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

### Keys

| key | what it does |
|---|---|
| `enter` | resume here — this terminal becomes the session |
| `ctrl-t` | resume in a **new tab**, leaving the shell you were in alone |
| `ctrl-y` | copy `cd … && claude --resume …` to the clipboard |
| `ctrl-o` | read the **whole transcript** in your pager — no resume, no tokens spent |
| `ctrl-s` | scope: all projects ⇄ only the directory you launched from |
| `ctrl-g` | agent: claude+codex → claude only → codex only |
| `ctrl-x` | automation: show or hide plugin/SDK-spawned runs |
| `ctrl-r` | order: best match ⇄ newest first |
| `ctrl-/` `ctrl-\` | toggle the preview / move it right → bottom → hidden |
| `f1` | key list, in the preview pane |

The four filter keys are the part `claude --resume` and `codex resume` don't have: you narrow
**without retyping the query or restarting the process**, and the header always says what is
currently on. Filters reset at every launch, so one you flipped last week can't quietly hide
half your sessions today. Add `--no-resume` to print the resume command instead of running it.

**Reading beats resuming, often.** Most of the time you only want to check that this is the
right session, or lift one answer out of it — `ctrl-o` gives you the full conversation in a
pager, matches marked `▶`, without starting a CLI or loading a context window.

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

## How it works

- Walks `~/.claude/projects/**/*.jsonl`, extracting user prompts and assistant text (one row
  per message) plus each session's AI-generated title.
- Caches parsed output per file, keyed by mtime, under `~/.cache/agsearch/`. Only changed
  sessions are re-parsed on later runs, so **you never index by hand** — every run refreshes
  incrementally (~0.15s warm, ~3s for a cold build over ~970 sessions). `--reindex` is a
  force-rebuild escape hatch, not routine maintenance.
- `--thinking` keeps its own cache under `~/.cache/agsearch/thinking/`, so alternating between
  plain and `--thinking` doesn't make each invalidate the other. Note that Claude Code stores
  thinking blocks *encrypted* (`"thinking": ""` plus a signature), so on most corpora there is
  no thinking text to search — agsearch says so once rather than looking broken.
- The JSONL schema is Claude Code's internal format and can change between releases; if a
  future version breaks parsing, run `agsearch --reindex` after updating the extractor.
- Ranking is covered by tests over a small fixture corpus (no dependencies, no fixtures on
  disk): `python3 -m unittest discover -s tests`.
