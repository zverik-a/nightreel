# Records docs/demo.gif with the offline demo provider (no real site content).
# Run from the repo root:  vhs docs/demo.tape
#
# vhs is slow: keys typed while the app is switching screens get lost, so every screen
# change is followed by a generous Sleep.
Output docs/demo.gif

Set Shell "bash"
Set FontSize 16
Set Width 1280
Set Height 720
Set Padding 16
Set Theme "Catppuccin Mocha"
Set TypingSpeed 80ms

Hide
Type "export PATH=$PWD/.venv/bin:$PATH NIGHTREEL_PROVIDER=demo NIGHTREEL_AGE_CONFIRMED=1 NIGHTREEL_THUMBNAILS=0"
Enter
Type "export XDG_CONFIG_HOME=$(mktemp -d) XDG_DATA_HOME=$(mktemp -d) XDG_STATE_HOME=$(mktemp -d) XDG_CACHE_HOME=$(mktemp -d) PS1='$ '"
Enter
Type "clear"
Enter
Sleep 500ms
Show

Type "nightreel"
Sleep 400ms
Enter
Sleep 2.5s

# --- search -------------------------------------------------------------------
Type "sea"
Sleep 700ms
Enter
Sleep 2.5s
Type "night"
Sleep 500ms
Enter
Sleep 3s
Down
Sleep 700ms
Down
Sleep 700ms
Down
Sleep 1.5s

# favorite the highlighted video (cursor stays put)
Ctrl+F
Sleep 2.5s

# multi-select two, open the actions menu
Tab
Sleep 600ms
Tab
Sleep 1s
Enter
Sleep 3s
Escape
Sleep 2.5s
Escape
Sleep 2.5s

# --- top rated ----------------------------------------------------------------
Type "top"
Sleep 700ms
Enter
Sleep 3s
Down
Sleep 600ms
Down
Sleep 1.5s
Ctrl+N
Sleep 3s
Escape
Sleep 2.5s

# --- favorites ----------------------------------------------------------------
Type "favo"
Sleep 700ms
Enter
Sleep 3s

# --- panic key: instant exit, screen and scrollback wiped -----------------------
Ctrl+X
Sleep 2s
