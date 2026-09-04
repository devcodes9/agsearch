---
name: agsearch
description: Search past Claude Code and Codex sessions saved on this machine. Use when the user refers to earlier work ("what did we decide about X", "we hit this error before"), asks to continue or hand off work started in another session, or when you are about to say you have no record of a conversation that happened before this one.
---

# agsearch

Every Claude Code and Codex session on this machine is a transcript on disk. `agsearch`
searches what was said inside them and prints ranked hits. You do not remember those
sessions. The transcripts do.

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
or an identifier. If that finds nothing, stop and say the conversation is not on this machine.
That is a real answer, and a more useful one than a guess.

Reach for the transcripts through `agsearch` rather than reading them directly. They are JSONL
with tool calls, diffs and base64 attachments interleaved, so grepping them returns matches
from machine noise rather than from anything anyone said.

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

## What this cannot do

Matching is lexical, not semantic. A session that discussed an idea in different words will
not surface, so a search returning nothing is weak evidence that a conversation never
happened. Everything runs locally against files already on disk, and nothing leaves the
machine.
