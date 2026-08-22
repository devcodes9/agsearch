# VHS tape for the README demo GIF.  https://github.com/charmbracelet/vhs
#
#   ./docs/record-demo.sh
#
# Recorded against a SYNTHETIC corpus, never a real ~/.claude. The GIF is the
# most-shared artifact this repo produces, so it must not contain a real
# transcript. record-demo.sh builds the fixture and points HOME at it.
#
# The query is deliberately misspelled: "conection pool" is what someone
# half-remembering a session actually types, and it exercises the subsequence
# fallback that makes the tagline true.

Output docs/demo.gif

Set Shell "bash"
Set FontSize 14
Set Width 1500
Set Height 500
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 75ms

Hide
Sleep 2s
Type "source @@ENV@@"
Enter
Sleep 800ms
Type "agsearch -n zzzznomatch >/dev/null 2>&1"
Enter
Sleep 2s
Type "clear"
Enter
Sleep 800ms
Show

Sleep 900ms
Type "agsearch"
Sleep 400ms
Enter

# One row per session, most recent first.
Sleep 2500ms

# Type the thing you half-remember, misspelled the way you would type it.
Type "conection pool"

# Row one is the session you meant; the pane shows the turn that proves it.
Sleep 4s

Screenshot docs/demo-still.png
Sleep 800ms
