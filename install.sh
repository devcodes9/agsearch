#!/bin/sh
# agsearch installer — drops the CLI on your PATH and checks its dependencies.
#
#   curl -fsSL https://raw.githubusercontent.com/devcodes9/agsearch/main/install.sh | sh
#
# By default this installs the latest tagged release. Override with:
#   AGSEARCH_VERSION=v0.1.0 sh install.sh    # a specific release
#   AGSEARCH_VERSION=main   sh install.sh    # unreleased tip, for testing
#   PREFIX=/usr/local/bin   sh install.sh    # a different install location
set -eu

REPO="devcodes9/agsearch"
PREFIX="${PREFIX:-$HOME/.local/bin}"
TARGET="$PREFIX/agsearch"

command -v python3 >/dev/null 2>&1 || {
  echo "error: python3 is required but not found on PATH." >&2
  exit 1
}

# Resolve which revision to install. Pinning to a tag is the point: without it
# every install is a different, unnamed build and nobody can say which one broke.
resolve_latest() {
  command -v curl >/dev/null 2>&1 || return 1
  curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" 2>/dev/null \
    | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
    | head -n 1
}

# A clone installs what is checked out; only a remote install needs a revision.
if [ -f "./agsearch" ] && [ -z "${AGSEARCH_VERSION:-}" ]; then
  mkdir -p "$PREFIX"
  install -m 0755 "./agsearch" "$TARGET"
  REF="$(git describe --tags --always --dirty 2>/dev/null || echo local)"
else
  REF="${AGSEARCH_VERSION:-}"
  if [ -z "$REF" ]; then
    REF="$(resolve_latest || true)"
    if [ -z "$REF" ]; then
      # No releases yet, or the API is unreachable / rate-limited. Say so rather
      # than silently serving an unnamed build.
      echo "note: could not resolve the latest release — falling back to main." >&2
      echo "      pin explicitly with: AGSEARCH_VERSION=v0.1.0 sh install.sh" >&2
      REF="main"
    fi
  fi

  mkdir -p "$PREFIX"
  URL="https://raw.githubusercontent.com/$REPO/$REF/agsearch"
  curl -fsSL "$URL" -o "$TARGET.tmp" || {
    rm -f "$TARGET.tmp"
    echo "error: could not download agsearch at '$REF'." >&2
    echo "       $URL" >&2
    echo "       check the version exists: https://github.com/$REPO/releases" >&2
    exit 1
  }
  # Download to .tmp and move into place only after it checks out, so a failed
  # or truncated fetch can never leave a broken agsearch on someone's PATH.
  head -n 1 "$TARGET.tmp" | grep -q '^#!' || {
    rm -f "$TARGET.tmp"
    echo "error: '$REF' did not resolve to an agsearch script." >&2
    exit 1
  }
  chmod 0755 "$TARGET.tmp"
  mv "$TARGET.tmp" "$TARGET"
fi

echo "installed: $TARGET ($REF)"

case ":$PATH:" in
  *":$PREFIX:"*) ;;
  *) echo "note: $PREFIX is not on your PATH — add it to your shell profile:"
     echo "      export PATH=\"$PREFIX:\$PATH\"" ;;
esac

if ! command -v fzf >/dev/null 2>&1; then
  echo "note: fzf is not installed — the interactive TUI needs it."
  echo "      macOS: brew install fzf   ·   Linux: see https://github.com/junegunn/fzf"
  echo "      (agsearch -n \"query\" works without fzf)"
  echo "      or skip both steps: brew install devcodes9/tap/agsearch"
fi

echo "done. run: agsearch"
