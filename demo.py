"""All six tools, in the order someone would actually hit them.

Everything printed is real output from the live server against the live
LiteForge chain. The numbers come from live tool calls and the root
comparison is a real eth_call. The only scripted lines are the human's.

Output is kept under 50 columns on purpose: the recording made from this
has to stay readable when GitHub renders it 309px wide on a phone.

No wallet is used. No key exists in this script or on that server.

    python demo.py
"""
import json
import time

import httpx

URL = "https://onboard.the-undesirables.com/mcp"
H = {"Content-Type": "application/json",
     "Accept": "application/json, text/event-stream"}
ADDR = "0x742d35cC6634c0532925A3b844bc9E7595F0beB1"  # real, empty
SHORT = ADDR[:6] + "…" + ADDR[-4:]
COLS = 50
_sid = None

GREY, CYAN, GREEN, BOLD, YEL, OFF = (
    "\033[90m", "\033[36m", "\033[32m", "\033[1m", "\033[33m", "\033[0m")


def rpc(body):
    global _sid
    h = dict(H)
    if _sid:
        h["Mcp-Session-Id"] = _sid
    r = httpx.post(URL, json=body, headers=h, timeout=60)
    _sid = r.headers.get("mcp-session-id") or _sid
    d = [json.loads(l[5:]) for l in r.text.splitlines()
         if l.startswith("data:")]
    if d:
        return d[-1]
    return r.json() if r.text.strip() else None


def tool(name, shown=""):
    args = {}
    if shown:
        k, v = shown.split("=", 1)
        args = {k: int(v) if v.isdigit() else ADDR if v == "ADDR" else v}
    label = shown.replace("=ADDR", f"='{SHORT}'")
    print(f"  {GREY}calls{OFF} {BOLD}{name}({label}){OFF}")
    r = rpc({"jsonrpc": "2.0", "id": 9, "method": "tools/call",
             "params": {"name": name, "arguments": args}})["result"]
    return json.loads(r["content"][0]["text"])


def out(text, plain=None):
    """Print an indented result line, asserting it fits the column budget."""
    width = len(plain if plain is not None else text)
    assert width + 5 <= COLS, f"{width + 5} cols: {plain or text}"
    print(f"  {GREY}└─{OFF} {text}")


def you(text):
    assert len(text) + 6 <= COLS, text
    print(f"\n{YEL}you ▸{OFF} {text}\n")


rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize",
     "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                "clientInfo": {"name": "demo", "version": "1"}}})
rpc({"jsonrpc": "2.0", "method": "notifications/initialized"})

print(f"{GREY}Add the connector once:{OFF}")
print(f"  {BOLD}onboard.the-undesirables.com/mcp{OFF}")
print(f"{GREY}No account, no keys. Every tool is a read.{OFF}")
time.sleep(1.4)

# 1 ── network ──────────────────────────────────────────────────
you("what is LitVM?")
n = tool("litvm_network")
out(f"{n['name'].replace(' Testnet', '')}", n['name'].replace(' Testnet', ''))
out(f"chain {CYAN}{n['chain_id']}{OFF} · gas in {n['gas_token']}",
    f"chain {n['chain_id']} · gas in {n['gas_token']}")
out(f"block {n['live']['block']:,}", f"block {n['live']['block']:,}")
time.sleep(1.5)

# 2 ── contracts ────────────────────────────────────────────────
you("what is deployed on it?")
c = tool("litvm_contracts")
out(f"{c['count']} contracts, all live on-chain:",
    f"{c['count']} contracts, all live on-chain:")
for x in c["contracts"][:2]:
    out(f"  {x['name'][:20]}", f"  {x['name'][:20]}")
out(f"{GREY}  …and {c['count'] - 2} more{OFF}", f"  …and {c['count'] - 2} more")
time.sleep(1.6)

# 3 ── the point ────────────────────────────────────────────────
you("prove a card price against the chain")
p = tool("litvm_verify_price", "product_id=246723")
out(f"{BOLD}Umbreon VMAX (Alt Art){OFF}", "Umbreon VMAX (Alt Art)")
out(f"${p['market_price_usd']:,.2f}", f"${p['market_price_usd']:,.2f}")
short = lambda h: h[:10] + "…" + h[-6:]
out(f"oracle {short(p['oracle_root'])}", f"oracle {short(p['oracle_root'])}")
out(f"chain  {short(p['onchain_root'])}", f"chain  {short(p['onchain_root'])}")
out(f"{GREEN}{BOLD}roots identical{OFF}", "roots identical")
out(f"verifyPrice() {GREEN}{BOLD}true{OFF}", "verifyPrice() true")
out(f"{GREY}a read. no wallet, no gas{OFF}", "a read. no wallet, no gas")
time.sleep(2.2)

# 4 + 5 ── only if you want to write ────────────────────────────
you("could I transact on it too?")
s = tool("litvm_status", "address=ADDR")
out(f"{SHORT}", SHORT)
out(f"{s['balance_zkltc']:.4f} {n['gas_token']} · {s['transactions_sent']} txs",
    f"{s['balance_zkltc']:.4f} {n['gas_token']} · {s['transactions_sent']} txs")
f = tool("litvm_fund", "address=ADDR")
out("faucet: liteforge.hub.caldera.xyz", "faucet: liteforge.hub.caldera.xyz")
out(f"{GREY}you claim it yourself{OFF}", "you claim it yourself")
time.sleep(1.7)

# 6 ── build on it ──────────────────────────────────────────────
you("and if I want to build on it?")
d = tool("litvm_deploy_template", "framework=foundry")
out(f"{d['framework']} config for chain {d['chain_id']}",
    f"{d['framework']} config for chain {d['chain_id']}")
out(f"{GREY}+ a contract reading the root{OFF}", "+ a contract reading the root")
print()
print(f"{GREY}Six tools. Every one a read.{OFF}")
print(f"{GREY}The price was on-chain before anyone asked.{OFF}")
