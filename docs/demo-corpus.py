"""Synthetic session corpus for the README demo.

Invented content only. The real ~/.claude and ~/.codex are never read, so the
GIF cannot leak a client transcript.
"""
import json, os, sys, hashlib, random
from datetime import datetime, timedelta

HOME = sys.argv[1]
random.seed(11)
base = datetime(2026, 8, 20, 9, 0, 0)

SESSIONS = [
    ("payments-api", "Webhook retries are firing twice on 500s", [
        ("user", "our stripe webhook handler retries immediately on a 500 and we end up charging twice. what should the backoff be?"),
        ("assistant", "Two separate bugs. The retry has no backoff, and the handler is not idempotent, so a duplicate delivery re-runs the charge."),
        ("user", "so we need both?"),
        ("assistant", "Yes. Add exponential backoff at 1s/4s/16s with jitter, capped at 3 attempts, and key the handler on the Stripe event id so a replay is a no-op. The connection pool was also saturating during retry storms."),
    ]),
    ("payments-api", "Refund flow returns 402 for partial amounts", [
        ("user", "partial refunds return 402 but full refunds are fine"),
        ("assistant", "The amount is being sent in dollars, not cents. Full refunds happen to work because you omit the field entirely."),
    ]),
    ("api", "Postgres connection pool exhausted under load", [
        ("user", "we keep hitting 'remaining connection slots are reserved' at about 200 rps"),
        ("assistant", "The pool is sized per-process but you run 8 workers, so 8x20 = 160 connections against a max_connections of 100."),
        ("user", "what should the pool size actually be?"),
        ("assistant", "Set the per-process pool to max_connections divided by worker count, minus a few for migrations and psql. With 100 and 8 workers that is 10, not 20. PgBouncer in transaction mode is the other option if you need more headroom."),
    ]),
    ("api", "Add rate limiting to the upload endpoint", [
        ("user", "we need per-user rate limits on /upload before launch"),
        ("assistant", "A sliding window in Redis keyed on user id is the simplest thing that holds up. Token bucket if you want to allow short bursts."),
    ]),
    ("web", "Flaky test only fails on CI, never locally", [
        ("user", "test_checkout_total fails maybe 1 in 5 runs on ubuntu but never on my mac"),
        ("assistant", "It depends on dict ordering from a set, which differs by hash seed. CI sets PYTHONHASHSEED=random."),
    ]),
    ("web", "Dark mode flashes white on first paint", [
        ("user", "there is a white flash before the dark theme applies"),
        ("assistant", "The theme is applied after hydration. Inline a small script in the head that reads localStorage and sets the class before first paint."),
    ]),
    ("infra", "Migrate the session store from memory to Redis", [
        ("user", "sessions are lost on every deploy because they live in process memory"),
        ("assistant", "Move them to Redis with a TTL matching your session lifetime. Keep the cookie signing secret in the environment so rotating it does not require a schema change."),
    ]),
    ("infra", "Terraform plan wants to recreate the whole VPC", [
        ("user", "plan says it will destroy and recreate the vpc, I only renamed a tag"),
        ("assistant", "The name is part of the resource address, so renaming it looks like a replacement. Use a moved block instead."),
    ]),
    ("cli-tool", "Argument parser swallows unknown flags", [
        ("user", "a typo in a flag silently becomes a search term instead of an error"),
        ("assistant", "Reject anything starting with a dash that is not a known flag, and add -- as the escape hatch for a literal query."),
    ]),
    ("cli-tool", "Ship a Homebrew formula for the CLI", [
        ("user", "what do I need for brew install to work"),
        ("assistant", "A tap repo, a formula with the tarball sha256, and a test block that does more than check --version."),
    ]),
    ("docs-site", "Search index is stale after a deploy", [
        ("user", "docs search returns pages that no longer exist"),
        ("assistant", "The index is built at image build time but served from a volume that survives deploys. Rebuild it in an entrypoint step."),
    ]),
    ("docs-site", "Code blocks lose syntax highlighting in dark mode", [
        ("user", "highlighting disappears when the theme switches"),
        ("assistant", "Two stylesheets are loaded and the dark one wins the cascade without defining token colours."),
    ]),
]

def write(project, title, turns, idx, source="cc"):
    cwd = os.path.join(HOME, "code", project)
    os.makedirs(cwd, exist_ok=True)   # else every row shows "orig dir gone"
    sid = hashlib.md5(f"{project}{title}".encode()).hexdigest()
    sid = f"{sid[:8]}-{sid[8:12]}-{sid[12:16]}-{sid[16:20]}-{sid[20:32]}"
    ts0 = base - timedelta(hours=idx * 7, minutes=idx * 13)
    if source == "cc":
        d = os.path.join(HOME, ".claude", "projects", cwd.replace("/", "-"))
        os.makedirs(d, exist_ok=True)
        lines = []
        for i, (role, text) in enumerate(turns):
            ts = (ts0 + timedelta(minutes=i * 3)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            content = text if role == "user" else [{"type": "text", "text": text}]
            e = {"type": role, "sessionId": sid, "cwd": cwd, "timestamp": ts,
                 "message": {"role": role, "content": content}}
            lines.append(json.dumps(e))
        lines.insert(0, json.dumps({"type": "ai-title", "aiTitle": title, "sessionId": sid}))
        open(os.path.join(d, sid + ".jsonl"), "w").write("\n".join(lines))
    else:
        d = os.path.join(HOME, ".codex", "sessions")
        os.makedirs(d, exist_ok=True)
        ents = [{"type": "session_meta", "payload": {"id": sid, "cwd": cwd,
                 "timestamp": ts0.strftime("%Y-%m-%dT%H:%M:%S")}}]
        for i, (role, text) in enumerate(turns):
            ts = (ts0 + timedelta(minutes=i * 3)).strftime("%Y-%m-%dT%H:%M:%S")
            ents.append({"type": "response_item", "timestamp": ts,
                         "payload": {"type": "message", "role": role,
                                     "content": [{"text": text}]}})
        open(os.path.join(d, sid + ".jsonl"), "w").write("\n".join(json.dumps(e) for e in ents))

for i, (proj, title, turns) in enumerate(SESSIONS):
    write(proj, title, turns, i, source="codex" if i in (5, 9) else "cc")
print(f"wrote {len(SESSIONS)} sessions under {HOME}")

# Filler so the list reads like a real corpus rather than a fixture. Titles only
# need to be plausible; the demo query never matches these.
FILLER = [
 ("web","Fix layout shift on the pricing table"),("web","Upgrade to React 19 and drop the compat shim"),
 ("web","Sticky header overlaps anchor links"),("web","Lazy-load the marketing hero image"),
 ("api","Return 409 instead of 500 on duplicate slug"),("api","Paginate the activity feed endpoint"),
 ("api","Move API keys out of the query string"),("api","Add request ids to every log line"),
 ("api","Cache the org lookup for the auth middleware"),("infra","Rotate the deploy key without downtime"),
 ("infra","Split staging and prod state files"),("infra","Alert when the certificate is 30 days from expiry"),
 ("infra","Cut the Docker image from 1.2GB to 300MB"),("infra","Autoscaling never scales back down"),
 ("payments-api","Reconcile Stripe payouts against the ledger"),("payments-api","Handle SCA redirects on renewal"),
 ("payments-api","Proration is off by one day on upgrades"),("cli-tool","Colour output breaks when piped"),
 ("cli-tool","Add shell completions for zsh and fish"),("cli-tool","Config file lookup ignores XDG paths"),
 ("cli-tool","Progress bar writes to stdout instead of stderr"),("docs-site","Broken links checker in CI"),
 ("docs-site","Version switcher drops the current page"),("docs-site","Add copy buttons to code blocks"),
 ("mobile","Keyboard covers the input on small screens"),("mobile","Offline queue replays twice after reconnect"),
 ("mobile","Deep links open the wrong tab"),("data","Backfill job times out on the largest tenant"),
 ("data","Dedupe events by idempotency key"),("data","Nightly export silently drops null columns"),
 ("data","Partition the events table by month"),("web","Form validation fires before first blur"),
 ("api","Rate limit headers are missing on 429"),("infra","CI cache never hits on forks"),
 ("payments-api","Invoice PDF renders the wrong currency symbol"),("cli-tool","--version exits 1 on Windows"),
 ("docs-site","Search returns results from old versions"),("mobile","Push token not refreshed after reinstall"),
 ("data","Timezone drift in the daily rollup"),("web","Focus ring invisible in dark mode"),
]
for j, (proj, title) in enumerate(FILLER):
    write(proj, title, [
        ("user", title.lower()),
        ("assistant", "Looked into it and pushed a fix; details in the diff."),
    ], len(SESSIONS) + j, source="codex" if j % 7 == 0 else "cc")
print(f"plus {len(FILLER)} filler sessions")

# Backdate mtimes. agsearch marks a session written in the last few minutes as
# live (a red dot); freshly generated fixtures would all look live, which is a
# lie the demo should not tell.
import time
for root, _d, files in os.walk(HOME):
    for f in files:
        if f.endswith(".jsonl"):
            p = os.path.join(root, f)
            age = 3600 * (6 + (hash(f) % 200))
            os.utime(p, (time.time() - age, time.time() - age))
print("backdated session mtimes")
