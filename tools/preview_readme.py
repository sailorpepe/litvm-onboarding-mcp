"""Render README.md the way GitHub would, for local review before pushing.

Writes _preview.html next to the README so relative asset paths (assets/*.png,
assets/demo.gif) resolve exactly as they will on GitHub. Serve the repo root
over HTTP and open it. _preview.html is gitignored.

    python tools/preview_readme.py && python -m http.server 8479
"""
import pathlib
import re

import json
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
src = (HERE / "README.md").read_text()

# Render with GITHUB'S OWN renderer, not a local markdown library. Python-Markdown
# does not parse markdown nested inside an HTML block, so a README that opens with
# <div align="center"> came out as a wall of literal markdown — a preview that
# lied about the file. GitHub's /markdown endpoint in gfm mode is the real thing.
payload = json.dumps({"text": src, "mode": "gfm"})
proc = subprocess.run(
    ["gh", "api", "--method", "POST", "/markdown", "--input", "-"],
    input=payload, capture_output=True, text=True,
)
if proc.returncode:
    print("GitHub render failed:", proc.stderr[-300:], file=sys.stderr)
    sys.exit(1)
body = proc.stdout

CSS = """
:root {
  --ground:#ffffff; --ink:#1f2328; --muted:#59636e; --edge:#d1d9e0;
  --sunken:#f6f8fa; --link:#0969da;
}
@media (prefers-color-scheme: dark) {
  :root { --ground:#0d1117; --ink:#e6edf3; --muted:#9198a1; --edge:#3d444d;
          --sunken:#151b23; --link:#4493f8; }
}
* { box-sizing:border-box; }
body {
  background:var(--ground); color:var(--ink); margin:0;
  font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
}
.page { max-width:1012px; margin:0 auto; padding:32px 32px 96px; }
.bar {
  border-bottom:1px solid var(--edge); padding:14px 0; margin-bottom:28px;
  font:12.5px ui-monospace,SFMono-Regular,Menlo,monospace; color:var(--muted);
}
.bar b { color:var(--ink); }
h1,h2,h3 { line-height:1.25; margin:24px 0 16px; }
h1 { font-size:2em; padding-bottom:.3em; border-bottom:1px solid var(--edge); }
h2 { font-size:1.5em; padding-bottom:.3em; border-bottom:1px solid var(--edge); }
p,ul,ol { margin:0 0 16px; }
a { color:var(--link); text-decoration:none; }
a:hover { text-decoration:underline; }
img { max-width:100%; }
code {
  background:var(--sunken); border-radius:6px; padding:.2em .4em;
  font:85% ui-monospace,SFMono-Regular,Menlo,monospace;
}
pre {
  background:var(--sunken); border-radius:6px; padding:16px; overflow:auto;
  font:85% ui-monospace,SFMono-Regular,Menlo,monospace; line-height:1.45;
}
pre code { background:none; padding:0; }
table { border-collapse:collapse; margin:0 0 16px; display:block; overflow:auto; }
th,td { border:1px solid var(--edge); padding:6px 13px; }
th { background:var(--sunken); font-weight:600; }
tr:nth-child(2n) td { background:var(--sunken); }
blockquote {
  margin:0 0 16px; padding:0 1em; color:var(--muted);
  border-left:.25em solid var(--edge);
}
hr { border:0; border-top:1px solid var(--edge); margin:24px 0; }
sub { color:var(--muted); }
"""

html = f"""<!doctype html><meta charset="utf-8">
<title>README preview — litvm-onboard</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{CSS}</style>
<div class="page">
  <div class="bar">sailorpepe / <b>litvm-onboarding-mcp</b> / <b>README.md</b>
    &nbsp;&middot;&nbsp; local preview, not pushed</div>
  {body}
</div>
"""
out = HERE / "_preview.html"
out.write_text(html)
print(f"wrote {out.relative_to(HERE)}  ({len(html):,} bytes)")

missing = [
    m for m in re.findall(r'(?:src|srcset)="([^"]+)"', src)
    if not m.startswith("http") and not (HERE / m).exists()
]
print("missing assets:", missing or "none")
