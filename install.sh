#!/bin/sh
# Install agsearch to ~/.local/bin (or $PREFIX).
#
#   curl -fsSL https://raw.githubusercontent.com/devcodes9/agsearch/main/install.sh | sh
#
# Installs the latest tagged release. Override with:
#   AGSEARCH_VERSION=v0.1.0 sh install.sh    # a specific release
#   AGSEARCH_VERSION=main   sh install.sh    # unreleased tip, for testing
#   PREFIX=/usr/local/bin   sh install.sh    # a different install location
#   AGSEARCH_SKILL=0        sh install.sh    # skip the Claude Code skill
set -eu

REPO="devcodes9/agsearch"
PREFIX="${PREFIX:-$HOME/.local/bin}"
TARGET="$PREFIX/agsearch"
MAIN_URL="https://raw.githubusercontent.com/$REPO/main/agsearch"

command -v python3 >/dev/null 2>&1 || {
  echo "error: python3 is required." >&2
  exit 1
}

# Download to .tmp and validate before moving into place, so a truncated fetch
# or a 404 body can never leave a broken agsearch on someone's PATH.
fetch() {
  curl -fsSL "$1" -o "$TARGET.tmp" 2>/dev/null || { rm -f "$TARGET.tmp"; return 1; }
  head -n 1 "$TARGET.tmp" | grep -q '^#!' || { rm -f "$TARGET.tmp"; return 1; }
}

mkdir -p "$PREFIX"

if [ -f "./agsearch" ] && [ -z "${AGSEARCH_VERSION:-}" ]; then
  install -m 0755 "./agsearch" "$TARGET"        # local checkout
else
  command -v curl >/dev/null 2>&1 || {
    echo "error: curl is required to install remotely." >&2
    exit 1
  }
  # /releases/latest/download resolves the newest tag server-side. No API call,
  # so no 60-request/hour rate limit and no JSON to parse.
  case "${AGSEARCH_VERSION:-}" in
    "")     URL="https://github.com/$REPO/releases/latest/download/agsearch" ;;
    main)   URL="$MAIN_URL" ;;
    *)      URL="https://github.com/$REPO/releases/download/$AGSEARCH_VERSION/agsearch" ;;
  esac

  if ! fetch "$URL"; then
    if [ -n "${AGSEARCH_VERSION:-}" ]; then
      echo "error: could not download agsearch from $URL" >&2
      echo "       check the version exists: https://github.com/$REPO/releases" >&2
      exit 1
    fi
    # No tagged release yet. Say so rather than failing the install outright.
    echo "note: no tagged release found — installing from main." >&2
    fetch "$MAIN_URL" || {
      echo "error: could not download agsearch from $MAIN_URL" >&2
      exit 1
    }
  fi
  chmod 0755 "$TARGET.tmp"
  mv "$TARGET.tmp" "$TARGET"
fi

# Read the version out of the file rather than running it: a freshly downloaded
# script should not be executed just to print a label.
VERSION="$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' "$TARGET" | head -n 1)"
echo "installed: $TARGET${VERSION:+ (v$VERSION)}"

case ":$PATH:" in
  *":$PREFIX:"*) ;;
  *) echo "note: $PREFIX is not on your PATH — add it to your shell profile:"
     echo "      export PATH=\"$PREFIX:\$PATH\"" ;;
esac

if ! command -v fzf >/dev/null 2>&1; then
  echo "note: fzf is not installed — the interactive TUI needs it."
  echo "      fzf 0.35 or newer: https://github.com/junegunn/fzf#installation"
  echo "      (agsearch -n \"query\" works without fzf)"
fi

# The skill is what lets a coding agent search these transcripts itself, so the one-line
# install should deliver it too. Taken from the checkout when there is one, fetched otherwise:
# this script never executes the binary it just downloaded, and a pinned older release has no
# --install-skill to call.
if [ "${AGSEARCH_SKILL:-1}" != "0" ]; then
  SKILL_REF="${AGSEARCH_VERSION:-main}"
  SKILL_DIR="$HOME/.claude/skills/agsearch"
  SKILL_URL="https://raw.githubusercontent.com/$REPO/$SKILL_REF/skills/agsearch/SKILL.md"
  if [ -f "$SKILL_DIR/SKILL.md" ]; then
    echo "note: $SKILL_DIR/SKILL.md exists — leaving it alone."
    echo "      to replace it: agsearch --install-skill --force"
  elif { [ -f "./skills/agsearch/SKILL.md" ] && [ -z "${AGSEARCH_VERSION:-}" ] &&
         cp "./skills/agsearch/SKILL.md" "$TARGET.skill"; } ||
       { curl -fsSL "$SKILL_URL" -o "$TARGET.skill" 2>/dev/null &&
         head -n 1 "$TARGET.skill" | grep -q '^---$'; }; then
    mkdir -p "$SKILL_DIR"
    mv "$TARGET.skill" "$SKILL_DIR/SKILL.md"
    echo "installed skill: $SKILL_DIR/SKILL.md (start a new Claude Code session to pick it up)"
  else
    rm -f "$TARGET.skill"
    echo "note: could not fetch the Claude Code skill. Install it later: agsearch --install-skill"
  fi
fi

echo "done. run: agsearch"
