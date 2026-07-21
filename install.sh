#!/bin/sh
# agsearch installer — drops the CLI on your PATH and checks its dependencies.
#
#   curl -fsSL https://raw.githubusercontent.com/devcodes9/agsearch/main/install.sh | sh
#
# Override the install location with:  PREFIX=/usr/local/bin sh install.sh
set -eu

PREFIX="${PREFIX:-$HOME/.local/bin}"
RAW="https://raw.githubusercontent.com/devcodes9/agsearch/main/agsearch"
TARGET="$PREFIX/agsearch"

command -v python3 >/dev/null 2>&1 || {
  echo "error: python3 is required but not found on PATH." >&2
  exit 1
}

mkdir -p "$PREFIX"

if [ -f "./agsearch" ]; then
  install -m 0755 "./agsearch" "$TARGET"        # local checkout
else
  curl -fsSL "$RAW" -o "$TARGET"                # remote install
  chmod 0755 "$TARGET"
fi

echo "installed: $TARGET"

case ":$PATH:" in
  *":$PREFIX:"*) ;;
  *) echo "note: $PREFIX is not on your PATH — add it to your shell profile:"
     echo "      export PATH=\"$PREFIX:\$PATH\"" ;;
esac

if ! command -v fzf >/dev/null 2>&1; then
  echo "note: fzf is not installed — the interactive TUI needs it."
  echo "      macOS: brew install fzf   ·   Linux: see https://github.com/junegunn/fzf"
  echo "      (agsearch -n \"query\" works without fzf)"
fi

echo "done. run: agsearch"
