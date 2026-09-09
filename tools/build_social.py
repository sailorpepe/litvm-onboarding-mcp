"""Render the repository social preview: the card GitHub shows when the repo is
linked in Slack, X, or Discord. Without one, GitHub serves a generic grey card.

GitHub wants 1280x640 and under 1 MB. Designed at 640x320 and rendered at 2x so
the type stays crisp. One fixed image, so it commits to the dark treatment.

    python tools/build_social.py
"""
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build_hero import CHROME, card_data_uri, live_proof, short  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent.parent
W, H = 640, 320

HTML = """<!doctype html><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=Instrument+Sans:wght@400;500&family=Martian+Mono:wght@400;500;600&display=swap">
<style>
  * {{ box-sizing: border-box; margin: 0; }}
  html, body {{ width: {W}px; height: {H}px; }}
  body {{
    background: #0B0D0E; color: #F2EFE6;
    font-family: "Instrument Sans", system-ui, sans-serif;
    display: flex; gap: 26px; padding: 30px 34px; align-items: center;
  }}
  .slab {{
    flex: none; width: 132px; background: #141A1F; border: 1px solid #2A343D;
    border-radius: 6px; padding: 7px;
  }}
  .window {{
    position: relative; border-radius: 3px; overflow: hidden;
    aspect-ratio: 719 / 1000; background: #0B0D0E;
  }}
  .window img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
  .window::after {{
    content: ""; position: absolute; inset: 0; mix-blend-mode: color-dodge; opacity: .2;
    background: linear-gradient(107deg, transparent 12%, #FF7A75 24%, #FFED61 34%,
      #A8FF61 44%, #85FFF7 55%, #7A95FF 66%, #D875FF 76%, transparent 88%);
  }}
  .body {{ flex: 1; min-width: 0; }}
  .eyebrow {{
    font-family: "Martian Mono", monospace; font-size: 8px; letter-spacing: .18em;
    color: #64BFD3; text-transform: uppercase;
  }}
  h1 {{
    font-family: "Bricolage Grotesque", sans-serif; font-weight: 700;
    font-size: 34px; line-height: 1.04; letter-spacing: -.023em; margin: 11px 0 0;
  }}
  p {{ margin: 12px 0 0; font-size: 13.5px; line-height: 1.5; color: #9FB0B6; max-width: 34ch; }}
  .verdict {{
    margin-top: 17px; display: flex; align-items: baseline; gap: 9px;
    font-family: "Martian Mono", monospace; font-size: 10px;
  }}
  .verdict b {{ color: #15CA60; font-weight: 600; letter-spacing: .07em; }}
  .verdict span {{ color: #68848C; }}
  .url {{
    margin-top: 15px; font-family: "Martian Mono", monospace;
    font-size: 9.5px; color: #F2EFE6; letter-spacing: -.01em;
  }}
</style>
<div class="slab"><div class="window"><img src="{card}" alt=""></div></div>
<div class="body">
  <div class="eyebrow">LitVM &middot; LiteForge &middot; chain 4441</div>
  <h1>Prove a card price<br>against the chain.</h1>
  <p>Six read-only MCP tools. No wallet, no keys, no account.</p>
  <div class="verdict"><b>verifyPrice() TRUE</b><span>{root}</span></div>
  <div class="url">onboard.the-undesirables.com/mcp</div>
</div>
"""


def main():
    d = live_proof()
    html = HTML.format(W=W, H=H, card=card_data_uri(), root=short(d["root"]))
    src = HERE / "assets" / "_social.html"
    src.write_text(html)
    png = HERE / "assets" / "social-preview.png"
    subprocess.run([
        CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
        f"--screenshot={png}", f"--window-size={W},{H}",
        "--force-device-scale-factor=2", "--virtual-time-budget=8000",
        src.as_uri(),
    ], check=True, capture_output=True, timeout=180)
    src.unlink()
    kb = png.stat().st_size / 1024
    print(f"{png.name}: {kb:,.0f} KB  (GitHub caps the social preview at 1 MB)")
    assert kb < 1024, "over GitHub's 1 MB social-preview limit"


if __name__ == "__main__":
    sys.exit(main())
