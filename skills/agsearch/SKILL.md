---
name: agsearch
description: Use when the user refers to work from an earlier session ("what did we decide about X", "we hit this error before"), asks to continue or hand one off, or when you are about to say you have no record of a conversation that happened before this one. Not for earlier in this same conversation. Use this instead of grepping ~/.claude/projects, ~/.codex/sessions or any transcript directory yourself. Searches Claude Code, Codex, Cursor, opencode and Gemini CLI transcripts on this machine.
---

# agsearch

You do not remember your past sessions. The transcripts on disk do, and `agsearch` searches
what was said inside them.

## The command

Use `agsearch` from the PATH. When it is not there, this plugin ships a copy at
`"$CLAUDE_PLUGIN_ROOT/agsearch"`. Same program either way. Resolve it once and use that for
every command below.

If neither exists, say so and name `brew install devcodes9/tap/agsearch`, rather than
retrying.

Never read the transcripts directly. They are JSONL with tool calls, diffs and base64
attachments interleaved, so grepping them returns machine noise rather than anything anyone
said.

## Build the query from content words

Pass the nouns, error strings and identifiers. Question words match hundreds of sessions
and outweigh the two or three words that identify one.

    user: what did we decide about the webhook retry backoff?
    you:  agsearch -n "webhook retry backoff"

Two to four content words is the target. On a 247-query benchmark, content words alone put
the right session first 49% of the time; the same words left inside the question that carried
them scored 10% to 22%.

Pass the user's own vocabulary. Inflections and typos are handled, so `migration` finds
`migrate` and a misspelling still ranks.

## Read the results

Each hit is one session: id, date, agent, matched/total terms, project, title, then the line
that matched underneath.

The top hit is usually the right session, not always. Read the matched line before trusting
it, and name the session you are answering from so the user can check you.

**Too many hits.** Add a content word. Narrowing beats paging: the output caps and reports how
many it withheld.

**No hits.** Drop to the single most distinctive word, usually an error string, a library name
or an identifier.

If that finds nothing, ask the user which repository the work was in, then retry with
`--project`. Ask for the repository rather than the date: people recall a repo far better than
a week, and on a 247-query measurement it recovered about as many missed sessions (31% against
38% for a date window that has to be right to within seven days; a month-wide window recovered
13%, and a quarter-wide one nothing).

Say the conversation is not on this machine only after an *unfiltered* search came back empty,
and name the window you searched.

## Open a session

    agsearch read <id>

The id is the first field of a result row. Any unambiguous prefix works. Output is capped for
you: you get the opening turns and the closing turns, which is what tells you the goal and the
outcome.

To find something specific inside a long session, pass the terms as well:

    agsearch read <id> "retry backoff"

The turns that matched are marked and are kept ahead of the ending when the cap applies.
`--full` prints everything when you need the middle too.

## Handoff

When the user asks to continue work from an earlier session:

1. Find the session with the search above.
2. `agsearch read <id>`.
3. Report the goal, what was already done, and where it stopped.
4. Continue the work.

Step 3 is done when you can state all three from the transcript. If any of them is a guess,
read again with the terms you are missing, or with `--full`.

Where the work left commits or a pull request, read those too: the transcript carries the
reasoning and the discarded options, and git carries what actually shipped. Neither is the
whole story on its own.

This is not `claude --resume`. Resume moves you back into the old session in its own
directory. Handoff brings that context forward into the session you are in now.

## Scope a search

    agsearch -n "..." --here             # sessions from this directory's project only
    agsearch -n "..." --project myapp    # sessions whose path matches myapp

Use these when a query returns the right topic from the wrong repository.

A filter can remove the very session you are looking for, turning a buried result into a
confident "not found". If a filtered search returns nothing, drop the filter and search again.
Never conclude that a conversation does not exist from a filtered search.

## What this cannot do

Matching is lexical, not semantic. A session that discussed an idea in different words will
not surface, so a search returning nothing is weak evidence that a conversation never
happened.
