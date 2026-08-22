#!/bin/sh
# Record docs/demo.gif against a synthetic corpus.
#
#   brew install vhs && ./docs/record-demo.sh
#
# The fixture is the whole point. The GIF is the most-shared artifact this repo
# produces, so it must never contain a real transcript: this builds a throwaway
# HOME full of invented sessions and points agsearch at that instead.
set -eu

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

command -v vhs >/dev/null 2>&1 || { echo "error: vhs is required (brew install vhs)" >&2; exit 1; }

python3 docs/demo-corpus.py "$WORK/home" >/dev/null

cat > "$WORK/env.sh" <<ENV
export HOME="$WORK/home"
export XDG_CACHE_HOME="$WORK/cache"
export PATH="$ROOT:\$PATH"
export TERM=xterm-256color
export PS1='\$ '
ENV

# The tape is committed with a placeholder so it carries no machine-specific
# path; the real one is substituted into a temp copy at record time.
sed "s|@@ENV@@|$WORK/env.sh|g" docs/demo.tape > "$WORK/demo.tape"
vhs "$WORK/demo.tape"

echo "wrote docs/demo.gif"
