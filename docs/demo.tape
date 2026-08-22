# VHS tape for the README demo GIF.  https://github.com/charmbracelet/vhs
#
#   brew install vhs
#   vhs docs/demo.tape        # writes docs/demo.gif
#
# The tape is committed rather than just the GIF on purpose: re-recording after
# a UI change is `vhs docs/demo.tape`, not getting the take right again.
#
# Keep it under ~15 seconds. The demo's whole job is to show that row one is
# the session you meant — not to tour the flags.

Output docs/demo.gif

Set Shell "zsh"
Set FontSize 16
Set Width 1200
Set Height 640
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 60ms

Hide
Type "clear" Enter
Show

Sleep 700ms
Type "agsearch"
Sleep 400ms
Enter

# Cold list settles, then type the thing you half-remember.
Sleep 2s
Type "stripe tax"
Sleep 2500ms

# The point of the whole product: the preview pane already shows the matched
# line, highlighted, before spending a token.
Sleep 1500ms

# Enter resumes — into Claude Code or Codex, whichever the session came from.
Enter
Sleep 3s
