# Homebrew formula for agsearch.
#
# This file is the source of truth; it is copied into the tap repo
# (devcodes9/homebrew-tap, as Formula/agsearch.rb) on release. See
# docs/packaging/homebrew.md for the one-time tap setup and the release loop.
#
#   brew install devcodes9/tap/agsearch
#
class Agsearch < Formula
  desc "Search every Claude Code and Codex CLI session, then resume the right one"
  homepage "https://github.com/devcodes9/agsearch"
  url "https://github.com/devcodes9/agsearch/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  license "MIT"
  head "https://github.com/devcodes9/agsearch.git", branch: "main"

  # The whole reason to ship a formula: brew resolves fzf, so the TUI works
  # immediately instead of failing on first run with a "brew install fzf" note.
  depends_on "fzf"
  depends_on "python@3.13"

  def install
    bin.install "agsearch"
  end

  test do
    # Homebrew's cookbook calls a --version-only test insufficient, and it would
    # not prove much here anyway. This exercises the real path: index a corpus,
    # match a query, print the hit.
    #
    # Three traps this avoids, all found the hard way:
    #   - HOME must point inside testpath, or the sandbox blocks the cache write.
    #   - An empty HOME exits 1 ("No indexed sessions found"), so the fixture
    #     session has to exist before agsearch runs.
    #   - `-n` highlights every query term with ANSI codes even when piped, so
    #     "stripe tax id" is NOT a contiguous substring of the output. Assert on
    #     unhighlighted text instead.
    ENV["HOME"] = testpath
    ENV["XDG_CACHE_HOME"] = testpath/"cache"

    session = testpath/".claude/projects/-tmp-demo/11111111-2222-3333-4444-555555555555.jsonl"
    session.dirname.mkpath
    session.write <<~JSONL
      {"type":"user","sessionId":"11111111-2222-3333-4444-555555555555","cwd":"/tmp/demo","timestamp":"2026-01-01T00:00:00.000Z","message":{"role":"user","content":"where do we set the stripe tax id"}}
      {"type":"assistant","sessionId":"11111111-2222-3333-4444-555555555555","cwd":"/tmp/demo","timestamp":"2026-01-01T00:00:05.000Z","message":{"role":"assistant","content":[{"type":"text","text":"The stripe tax id lives in billing/config.py"}]}}
    JSONL

    assert_match version.to_s, shell_output("#{bin}/agsearch --version")

    hits = shell_output("#{bin}/agsearch -n \"stripe tax id\"")
    assert_match "billing/config.py", hits   # the matched line, unhighlighted
    assert_match "demo", hits                # resolved from the session's cwd
  end
end
