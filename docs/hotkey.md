# Optional: a global hotkey

agsearch does not need a hotkey. If you are running `claude` you are already at
a terminal prompt, and typing `agsearch` costs nothing — the window is already
focused.

A global hotkey solves a narrower problem: you are in Slack, a browser or Figma
and want a past session *without* first finding a terminal. That is a real
trigger, just a rarer one, which is why this lives in docs rather than in a
setup wizard.

The cheapest version of "launch it from anywhere" is not a hotkey at all:

```sh
alias ags=agsearch
```

Most people's actual friction is that the command is eight characters and they
forget it exists. (`ag` is taken — that is the silver searcher.)

If you want the real thing, pick whichever daemon you already run.

## Raycast

If you use Raycast, you already have the hotkey. Create a Script Command that
opens your terminal running `agsearch`, and bind it in Raycast's preferences.
Nothing else to install.

## Hammerspoon

In `~/.hammerspoon/init.lua`. Replace the terminal with the one you use — the
`tell application` block is the only part that differs.

```lua
-- iTerm2
hs.hotkey.bind({ "ctrl", "cmd" }, "k", function()
  hs.osascript.applescript([[
    tell application "iTerm"
      activate
      create window with default profile command "/bin/zsh -lic \"exec agsearch\""
    end tell]])
end)
```

```lua
-- Ghostty, kitty, WezTerm, Alacritty — anything that takes a command argument
hs.hotkey.bind({ "ctrl", "cmd" }, "k", function()
  hs.task.new("/opt/homebrew/bin/ghostty", nil, { "-e", "zsh", "-lic", "exec agsearch" }):start()
end)
```

```lua
-- Terminal.app
hs.hotkey.bind({ "ctrl", "cmd" }, "k", function()
  hs.osascript.applescript([[
    tell application "Terminal"
      activate
      do script "exec agsearch"
    end tell]])
end)
```

Reload with `hs.reload()` or the menu bar item.

## skhd

In `~/.skhdrc`:

```
ctrl + cmd - k : /opt/homebrew/bin/ghostty -e zsh -lic "exec agsearch"
```

`skhd --restart-service` to apply.

## Why the window "becomes" the session

Because each of these launches a shell whose whole job is `exec agsearch`, the
window is replaced by whatever you resume into. Press Enter on a result and the
floating window *is* the Claude Code session — close it and you are back where
you were.

## Linux

`sxhkd`, or your desktop environment's keyboard settings, pointed at the same
`$TERMINAL -e zsh -lic "exec agsearch"` shape.
