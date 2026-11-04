# Records docs/demo.gif with the offline demo provider (no real site content).
# Run from the repo root:  vhs docs/demo.tape
Output docs/demo.gif

Set Shell "bash"
Set FontSize 16
Set Width 1280
Set Height 720
Set Padding 16
Set Theme "Catppuccin Mocha"
Set TypingSpeed 70ms

Hide
Type "export PATH=$PWD/.venv/bin:$PATH NIGHTREEL_PROVIDER=demo NIGHTREEL_AGE_CONFIRMED=1 NIGHTREEL_THUMBNAILS=0"
Enter
Type "export XDG_CONFIG_HOME=$(mktemp -d) XDG_DATA_HOME=$(mktemp -d) XDG_STATE_HOME=$(mktemp -d) XDG_CACHE_HOME=$(mktemp -d) PS1='$ '"
Enter
Type "clear"
Enter
Show

Type "nightreel"
Sleep 400ms
Enter
Sleep 1.5s

# search
Type "sea"
Sleep 600ms
Enter
Sleep 600ms
Type "night"
Sleep 400ms
Enter
Sleep 2s
Down
Sleep 500ms
Down
Sleep 500ms
Down
Sleep 1.2s

# favorite the highlighted video, multi-select two more
Ctrl+F
Sleep 1.2s
Tab
Sleep 400ms
Tab
Sleep 800ms

# actions menu
Enter
Sleep 2s
Escape
Sleep 800ms
Escape
Sleep 800ms

# categories
Type "categ"
Sleep 500ms
Enter
Sleep 1.2s
Down
Sleep 400ms
Enter
Sleep 2s
Ctrl+N
Sleep 1.5s
Escape
Sleep 500ms
Escape
Sleep 800ms

# favorites
Type "favo"
Sleep 500ms
Enter
Sleep 2s

# panic key: instant exit, screen wiped
Ctrl+X
Sleep 1.5s
