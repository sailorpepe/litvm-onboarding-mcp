# Regenerate with: vhs demo.tape
# Every line in the recording is a real call to the live server.

Output assets/demo.gif

Set Shell "bash"
Set FontSize 16
Set Width 1180
Set Height 960
Set Padding 22
Set Theme "Catppuccin Mocha"
Set WindowBar Colorful
Set BorderRadius 10
Set CursorBlink false
Set TypingSpeed 60ms

Hide
Type "cd ~/mcp-hosts/litvm-onboard && clear"
Enter
Show

# run it hidden — the recording should show the experience, not my shell
Hide
Type "python demo.py"
Enter
Sleep 900ms
Show
Sleep 34s
