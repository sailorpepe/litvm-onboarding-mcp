"""Render the proof diagram: why a price cannot be faked after the fact.

The hero shows that verification succeeded. This shows the mechanism. Drawn as a
schematic tree of depth 4 because a real 19-level tree does not fit a README
column; the caption carries the real depth, read live.

Two conventions borrowed from how proofs are normally drawn: the root sits at the
top, and the SIBLING hashes are the ones highlighted, because the siblings are
what actually gets shipped. The path is just the journey.

Raster PNG: the GitHub mobile apps render no SVG in a README.

    python tools/build_diagram.py
"""
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build_hero import CHROME, THEMES, live_proof  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent.parent
W, H = 1040, 340
DEPTH, LEAF = 4, 5           # schematic only; the caption names the real depth
SVG_W, SVG_H, PAD = 430, 250, 14


def tree_svg(c):
    """Nodes, edges, and the highlighted proof for a depth-4 schematic."""
    def pos(level, i):
        span = (SVG_W - 2 * PAD) / (2 ** level)
        return PAD + (i + 0.5) * span, 22 + level * ((SVG_H - 44) / DEPTH)

    # walk from the leaf up, recording which node is on the path and which is its sibling
    path, siblings, idx = [], [], LEAF
    for level in range(DEPTH, 0, -1):
        path.append((level, idx))
        siblings.append((level, idx ^ 1))
        idx //= 2
    path.append((0, 0))
    path_set, sib_set = set(path), set(siblings)

    edges, nodes = [], []
    for level in range(DEPTH + 1):
        for i in range(2 ** level):
            x, y = pos(level, i)
            if level:
                px, py = pos(level - 1, i // 2)
                on = (level, i) in path_set or (level, i) in sib_set
                edges.append(
                    f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{x:.1f}" y2="{y:.1f}" '
                    f'stroke="{c["ink"] if on else c["edge"]}" '
                    f'stroke-width="{1.6 if on else .9}" opacity="{1 if on else .55}"/>')
            if (level, i) in sib_set:
                fill, stroke, r = c["accent"], c["accent"], 5.4
            elif (level, i) in path_set:
                fill, stroke, r = c["panel"], c["ink"], 5.4
            else:
                fill, stroke, r = "none", c["edge"], 3.4
            if level == 0:
                fill, stroke, r = c["ok"], c["ok"], 7.4
            nodes.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" '
                         f'stroke="{stroke}" stroke-width="1.6"/>')

    lx, ly = pos(DEPTH, LEAF)
    rx, ry = pos(0, 0)
    labels = (
        f'<text x="{rx + 14:.1f}" y="{ry + 3.5:.1f}" class="lbl">ROOT, ALREADY ON CHAIN</text>'
        f'<text x="{lx:.1f}" y="{ly + 20:.1f}" class="lbl mid">YOUR CARD</text>')
    return (f'<svg viewBox="0 0 {SVG_W} {SVG_H}" width="{SVG_W}" height="{SVG_H}">'
            + "".join(edges) + "".join(nodes) + labels + "</svg>")


HTML = """<!doctype html><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=Instrument+Sans:wght@400;500&family=Martian+Mono:wght@400;500;600&display=swap">
<style>
  * {{ box-sizing: border-box; margin: 0; }}
  html, body {{ width: {W}px; height: {H}px; }}
  body {{
    background: {ground}; color: {ink};
    font-family: "Instrument Sans", system-ui, sans-serif;
    display: flex; gap: 36px; padding: 26px 34px; align-items: center;
  }}
  .fig {{ flex: none; display: flex; flex-direction: column; gap: 9px; align-items: center; }}
  .lbl {{
    font-family: "Martian Mono", monospace; font-size: 8px;
    letter-spacing: .12em; fill: {muted};
  }}
  .mid {{ text-anchor: middle; }}
  .key {{
    display: flex; gap: 15px; font-family: "Martian Mono", monospace;
    font-size: 7.6px; letter-spacing: .07em; color: {muted}; text-transform: uppercase;
  }}
  .key i {{ display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 5px; }}
  .steps {{ flex: 1; min-width: 0; }}
  h2 {{
    font-family: "Bricolage Grotesque", sans-serif; font-weight: 700;
    font-size: 25px; letter-spacing: -.019em; margin-bottom: 15px;
  }}
  ol {{ list-style: none; display: flex; flex-direction: column; gap: 11px; }}
  li {{ display: flex; gap: 11px; font-size: 13px; line-height: 1.44; max-width: 52ch; }}
  li b {{
    flex: none; width: 17px; height: 17px; border-radius: 50%; margin-top: 1px;
    border: 1px solid {edge}; color: {muted}; font-family: "Martian Mono", monospace;
    font-size: 8px; display: flex; align-items: center; justify-content: center;
  }}
  li em {{ font-style: normal; color: {ink}; font-weight: 600; }}
  li span {{ color: {muted}; }}
</style>
<div class="fig">
  {svg}
  <div class="key">
    <span><i style="background:{accent}"></i>Sibling hashes &mdash; the proof</span>
    <span><i style="background:{ok}"></i>Root</span>
  </div>
</div>
<div class="steps">
  <h2>Why it cannot be faked</h2>
  <ol>
    <li><b>1</b><span>Every night the oracle publishes <em>one</em> root to LiteForge covering
      every one of {total} prices. That happens before anyone asks a question.</span></li>
    <li><b>2</b><span>Your card's price, plus <em>{depth} sibling hashes</em>, recompute that
      exact root. Change any figure and the result stops matching.</span></li>
    <li><b>3</b><span>The contract does the arithmetic itself and returns
      <em>true</em>. You are trusting the chain, not the oracle.</span></li>
  </ol>
</div>
"""


def main():
    d = live_proof()
    out = HERE / "assets"
    for theme, c in THEMES.items():
        html = HTML.format(W=W, H=H, svg=tree_svg(c),
                           total=f'{d["total_products"] // 10_000 * 10_000:,}+', depth=len(d["proof"]), **c)
        src = out / f"_diagram-{theme}.html"
        src.write_text(html)
        png = out / f"proof-{theme}.png"
        subprocess.run([
            CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
            f"--screenshot={png}", f"--window-size={W},{H}",
            "--force-device-scale-factor=2", "--virtual-time-budget=8000", src.as_uri(),
        ], check=True, capture_output=True, timeout=180)
        src.unlink()
        print(f"{png.name}: {png.stat().st_size / 1024:,.0f} KB")


if __name__ == "__main__":
    sys.exit(main())
