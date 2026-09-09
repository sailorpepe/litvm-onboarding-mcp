# Regenerate with: vhs demo.tape
# Every line in the recording is a real call to the live server.
#
# Geometry is deliberate. GitHub caps a README at 838px wide and 309px on a
# phone, and shrinks the image to fit. At Width 1160 / FontSize 28 the type
# lands at ~20px on a repo page. The demo output is held under 50 columns so
# nothing wraps. See demo.py.
#
# The run takes ~30s, so Sleep covers it and LoopOffset parks the still
# frame on the completed transcript, which is what reduce-motion readers see.
#
# Palette is sampled, not invented: the darks come from the Umbreon VMAX
# alternate art itself, the turquoise is LitVM's own brand token.

Output assets/demo.gif

Set Shell "bash"
Set FontSize 28
Set Width 1160
Set Height 1560
Set Padding 40
Set Margin 50
Set MarginFill "#333D4C"
Set BorderRadius 12
Set WindowBar Colorful
Set WindowBarSize 40
Set Framerate 24
Set CursorBlink false
Set TypingSpeed 60ms
Set LoopOffset 92%

Set Theme { "name": "slab", "background": "#0B0D0E", "foreground": "#F2EFE6", "cursor": "#64BFD3", "selection": "#333D4C", "black": "#0B0D0E", "red": "#C25A54", "green": "#15CA60", "yellow": "#EFCB40", "blue": "#64BFD3", "magenta": "#9E8FB2", "cyan": "#64BFD3", "white": "#F2EFE6", "brightBlack": "#68848C", "brightRed": "#C25A54", "brightGreen": "#15CA60", "brightYellow": "#EFCB40", "brightBlue": "#64BFD3", "brightMagenta": "#9E8FB2", "brightCyan": "#64BFD3", "brightWhite": "#FFFFFF" }

Hide
Type "cd ~/mcp-hosts/litvm-onboard && export PS1='' && shopt -s expand_aliases && alias python=.venv/bin/python && clear"
Enter
Show

Hide
Type "python demo.py"
Enter
Sleep 900ms
Show
Sleep 33s
