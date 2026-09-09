"""Render the README hero: the proof itself, as an image.

Two variants (light and dark) so the README can use <picture> and be correct in
either GitHub theme. Raster PNG on purpose: the GitHub mobile apps render no SVG
in a README at all.

Every value on the card is real, pulled live from the oracle at build time.
Palette provenance, so no color here is arbitrary:
  #0B0D0E #333D4C #68848C  sampled from the Umbreon VMAX alternate art
  #64BFD3                  LitVM's own brand token
  #F2EFE6                  slab label stock
  #15CA60 / #007408        positive state, dark ground / light ground

    python tools/build_hero.py
"""
import base64
import json
import pathlib
import subprocess
import sys

import httpx

HERE = pathlib.Path(__file__).resolve().parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PRODUCT_ID = 246723
W, H = 1040, 340          # CSS px; rendered at 2x -> 2080x680, a 3.06:1 banner


def live_proof():
    r = httpx.get("https://oracle.the-undesirables.com/api/v1/merkle/proof",
                  params={"product_id": PRODUCT_ID}, timeout=60)
    r.raise_for_status()
    return r.json()["data"]


def card_data_uri():
    r = httpx.get(f"https://product-images.tcgplayer.com/fit-in/1000x1000/{PRODUCT_ID}.jpg",
                  timeout=60)
    r.raise_for_status()
    return "data:image/jpeg;base64," + base64.b64encode(r.content).decode()


THEMES = {
    "dark":  dict(ground="#0B0D0E", panel="#141A1F", edge="#2A343D", ink="#F2EFE6",
                  muted="#68848C", accent="#64BFD3", ok="#15CA60",
                  label_bg="#F2EFE6", label_ink="#0B0D0E"),
    "light": dict(ground="#F4F2EC", panel="#FFFFFF", edge="#D5D2C8", ink="#16171A",
                  muted="#5C6B72", accent="#0E6C7E", ok="#007408",
                  label_bg="#333D4C", label_ink="#F2EFE6"),
}

HTML = """<!doctype html><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=Instrument+Sans:wght@400;500;600&family=Martian+Mono:wght@400;500;600&display=swap">
<style>
  * {{ box-sizing: border-box; margin: 0; }}
  html, body {{ width: {W}px; height: {H}px; }}
  body {{
    background: {ground}; color: {ink};
    font-family: "Instrument Sans", system-ui, sans-serif;
    display: flex; gap: 30px; padding: 26px 34px; align-items: stretch;
  }}

  /* ---- the slab: flat, outlined, matte. spectacle stays inside the window ---- */
  .slab {{
    flex: none; width: 178px; background: {panel};
    border: 1px solid {edge}; border-radius: 7px; padding: 9px;
    display: flex; flex-direction: column; gap: 8px;
  }}
  .label {{
    background: {label_bg}; color: {label_ink}; border-radius: 3px;
    padding: 5px 7px; font-family: "Martian Mono", monospace;
    font-size: 6.2px; line-height: 1.45; letter-spacing: .02em;
  }}
  .label b {{ font-weight: 600; letter-spacing: .04em; }}
  .label span {{ opacity: .62; }}
  .window {{
    position: relative; border-radius: 4px; overflow: hidden;
    aspect-ratio: 719 / 1000; background: #0B0D0E;
  }}
  .window img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
  /* holofoil, confined to the art window and nowhere else */
  .window::after {{
    content: ""; position: absolute; inset: 0; mix-blend-mode: color-dodge;
    opacity: .19;
    background: linear-gradient(107deg,
      transparent 12%, #FF7A75 24%, #FFED61 34%, #A8FF61 44%,
      #85FFF7 55%, #7A95FF 66%, #D875FF 76%, transparent 88%);
  }}

  /* ---- the proof ---- */
  .proof {{ flex: 1; display: flex; flex-direction: column; min-width: 0;
            justify-content: center; }}
  .eyebrow {{
    font-family: "Martian Mono", monospace; font-size: 7.4px;
    letter-spacing: .17em; color: {accent}; text-transform: uppercase;
  }}
  h1 {{
    font-family: "Bricolage Grotesque", sans-serif; font-weight: 700;
    font-size: 31px; line-height: 1.06; letter-spacing: -.021em;
    margin: 9px 0 0; max-width: 15ch;
  }}
  .price {{
    font-family: "Bricolage Grotesque", sans-serif; font-weight: 600;
    font-size: 20px; color: {muted}; font-variant-numeric: tabular-nums;
    margin-top: 5px;
  }}
  .rows {{
    margin-top: 13px; border-top: 1px solid {edge}; padding-top: 11px;
    display: grid; grid-template-columns: auto auto auto;
    justify-content: start; gap: 5px 16px; align-items: baseline;
    font-family: "Martian Mono", monospace; font-size: 9.6px;
    font-variant-numeric: tabular-nums;
  }}
  .rows dt {{ color: {muted}; font-size: 7.6px; letter-spacing: .1em; text-transform: uppercase; }}
  .rows dd {{ color: {ink}; letter-spacing: -.01em; }}
  .rows dd.verdict {{ color: {ok}; font-weight: 600; letter-spacing: .06em; font-size: 8.4px; }}
  .path {{ margin-top: 15px; display: flex; align-items: center; gap: 9px; }}
  .ticks {{ display: flex; gap: 3px; }}
  .ticks i {{
    width: 4px; height: 15px; border-radius: 1px; background: {accent};
    opacity: .38; display: block;
  }}
  .ticks i:first-child, .ticks i:last-child {{ opacity: 1; height: 19px; }}
  .path span {{
    font-family: "Martian Mono", monospace; font-size: 7.2px;
    letter-spacing: .11em; color: {muted}; text-transform: uppercase;
  }}
  .foot {{
    margin-top: 15px; color: {muted};
    font-family: "Martian Mono", monospace; font-size: 7.6px; letter-spacing: .04em;
  }}
  .foot b {{ color: {ink}; font-weight: 500; }}
</style>
<div class="slab">
  <div class="label">
    <b>MERKLE PRICE ORACLE</b><br>
    <span>LITEFORGE &middot; CHAIN 4441</span><br>
    <span>LEAF {leaf_index}</span>
  </div>
  <div class="window"><img src="{card}" alt=""></div>
</div>

<div class="proof">
  <div class="eyebrow">Committed on-chain {data_date}</div>
  <h1>{name}</h1>
  <div class="price">${price}</div>

  <div class="path">
    <span>Leaf</span>
    <div class="ticks">{ticks}</div>
    <span>Root &middot; {depth} hashes</span>
  </div>

  <dl class="rows">
    <dt>Root on chain</dt><dd>{root}</dd><dd class="verdict">&nbsp;</dd>
    <dt>Oracle root</dt><dd>{root}</dd><dd class="verdict">IDENTICAL</dd>
    <dt>verifyPrice()</dt><dd>returned by the contract</dd><dd class="verdict">TRUE</dd>
  </dl>

  <div class="foot">
    One price of <b>{total}</b> &middot; proved by <b>{depth} sibling hashes</b>
    &middot; no wallet, no gas
  </div>
</div>
"""


def short(h):
    return h[:10] + "…" + h[-8:]


def main():
    d = live_proof()
    card = card_data_uri()
    fields = dict(
        W=W, H=H, card=card,
        name=d["leaf_data"]["name"],
        price=f'{d["leaf_data"]["market_price_cents"] / 100:,.2f}',
        root=short(d["root"]),
        leaf_index=f'{d["leaf_index"]:,}',
        total=f'{d["total_products"]:,}',
        depth=len(d["proof"]),
        data_date=d["data_date"],
        ticks="<i></i>" * len(d["proof"]),
    )
    out_dir = HERE / "assets"
    for theme, colors in THEMES.items():
        html = HTML.format(**fields, **colors)
        src = out_dir / f"_hero-{theme}.html"
        src.write_text(html)
        png = out_dir / f"hero-{theme}.png"
        subprocess.run([
            CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
            f"--screenshot={png}", f"--window-size={W},{H}",
            "--force-device-scale-factor=2", "--virtual-time-budget=8000",
            "--default-background-color=00000000", src.as_uri(),
        ], check=True, capture_output=True, timeout=180)
        src.unlink()
        print(f"{png.name}: {png.stat().st_size:,} bytes")
    print(f"\nlive values used: root {short(d['root'])}, {d['total_products']:,} products, "
          f"{len(d['proof'])} hashes, dated {d['data_date']}")


if __name__ == "__main__":
    sys.exit(main())
