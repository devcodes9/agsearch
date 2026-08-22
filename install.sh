#!/bin/sh
# Install agsearch to ~/.local/bin (or $PREFIX).
#
#   curl -fsSL https://raw.githubusercontent.com/devcodes9/agsearch/main/install.sh | sh
#
# Installs the latest tagged release. Override with:
#   AGSEARCH_VERSION=v0.1.0 sh install.sh    # a specific release
#   AGSEARCH_VERSION=main   sh install.sh    # unreleased tip, for testing
#   PREFIX=/usr/local/bin   sh install.sh    # a different install location
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

# Name the command for the machine this is running on. "see the fzf homepage"
# means going and reading a page; an exact line means running it. Printed, never
# run: installing system packages needs sudo, and a piped installer that sudos
# is the reason people distrust piped installers.
if ! command -v fzf >/dev/null 2>&1; then
  if   command -v brew    >/dev/null 2>&1; then FZF_HINT="brew install fzf"
  elif command -v apt-get >/dev/null 2>&1; then FZF_HINT="sudo apt install fzf"
  elif command -v dnf     >/dev/null 2>&1; then FZF_HINT="sudo dnf install fzf"
  elif command -v pacman  >/dev/null 2>&1; then FZF_HINT="sudo pacman -S fzf"
  elif command -v zypper  >/dev/null 2>&1; then FZF_HINT="sudo zypper install fzf"
  elif command -v apk     >/dev/null 2>&1; then FZF_HINT="sudo apk add fzf"
  else FZF_HINT=""
  fi
  echo "note: fzf is not installed — the interactive interface needs it."
  [ -n "$FZF_HINT" ] && echo "      $FZF_HINT"
  echo "      no sudo:  git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf && ~/.fzf/install"
  echo "      or skip it: agsearch -n \"query\" works without fzf"
fi

echo "done. run: agsearch"
