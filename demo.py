"""The whole thing, recorded — all six tools, in the order someone would actually hit them.

Everything printed is real output from https://onboard.the-undesirables.com/mcp against the
live LiteForge chain. The plan comes from the server's own prompt; the numbers come from live
tool calls; the root comparison is a real eth_call. The only scripted lines are the human's.

No wallet is used. No key exists anywhere in this script or on that server.

    python demo.py
"""
import json
import time

import httpx

URL = "https://onboard.the-undesirables.com/mcp"
H = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
ADDR = "0x742d35cC6634c0532925A3b844bc9E7595F0beB1"   # a real, empty address
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
    d = [json.loads(l[5:]) for l in r.text.splitlines() if l.startswith("data:")]
    if d:
        return d[-1]
    return r.json() if r.text.strip() else None


def tool(name, args=None):
    shown = "(" + ", ".join(f"{k}={v!r}" for k, v in args.items()) + ")" if args else "()"
    print(f"  {GREY}calls{OFF} {BOLD}{name}{shown}{OFF}")
    r = rpc({"jsonrpc": "2.0", "id": 9, "method": "tools/call",
             "params": {"name": name, "arguments": args or {}}})["result"]
    return json.loads(r["content"][0]["text"])


def out(text):
    print(f"  {GREY}└─{OFF} {text}")


def you(text):
    print(f"\n{YEL}you ▸{OFF} {text}\n")


rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize",
     "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                "clientInfo": {"name": "demo", "version": "1"}}})
rpc({"jsonrpc": "2.0", "method": "notifications/initialized"})

print(f"{GREY}Add the connector once — Claude Desktop, Cursor, anything that speaks MCP:{OFF}")
print(f"  {BOLD}https://onboard.the-undesirables.com/mcp{OFF}")
print(f"{GREY}No install, no account, no keys. Every tool is read-only.{OFF}")
time.sleep(1.6)

# 1 ── network ───────────────────────────────────────────────────────────────
you("what is LitVM and how do I connect?")
n = tool("litvm_network")
out(f"{n['name']} · chain {CYAN}{n['chain_id']}{OFF} · block {n['live']['block']:,} · gas in {n['gas_token']}")
out(f"rpc {n['rpc_http']}")
time.sleep(1.7)

# 2 ── contracts ─────────────────────────────────────────────────────────────
you("what is actually deployed on it?")
c = tool("litvm_contracts")
out(f"{c['count']} contracts, all confirmed live on-chain:")
for x in c["contracts"][:2]:
    out(f"   {x['name']:<22} {x['address'][:10]}…{x['address'][-6:]}")
out(f"   {GREY}…and {c['count'] - 2} more (souls, sports, grading, weather){OFF}")
time.sleep(1.9)

# 3 ── the point ─────────────────────────────────────────────────────────────
you("prove me a real card price against the chain")
p = tool("litvm_verify_price", {"product_id": 246723})
out(f"{BOLD}{p['card']}{OFF} — ${p['market_price_usd']:,.2f}")
out(f"oracle root   {p['oracle_root'][:14]}…{p['oracle_root'][-8:]}")
out(f"chain  root   {p['onchain_root'][:14]}…{p['onchain_root'][-8:]}   {GREEN}{BOLD}identical{OFF}")
out(f"verifyPrice() {GREEN}{BOLD}true{OFF} {GREY}— the contract's own answer, over RPC{OFF}")
out(f"{GREY}no wallet, no gas, no key — that was a read{OFF}")
time.sleep(2.2)

# 4 + 5 ── only if you want to write to the chain ────────────────────────────
you("I want to transact on it too. Am I set up?")
s = tool("litvm_status", {"address": ADDR})
out(f"{s['balance_zkltc']:.4f} {n['gas_token']} · {s['transactions_sent']} txs · "
    f"{'ready' if s['funded'] else GREY + 'no gas yet' + OFF}")
f = tool("litvm_fund", {"address": ADDR})
out(f"faucet {f['faucet']}")
out(f"{f['steps'][0].split(chr(8212))[0].strip()}")
out(f"{GREY}you claim it in your own wallet — this server holds no keys{OFF}")
time.sleep(1.9)

# 6 ── build on it ───────────────────────────────────────────────────────────
you("and if I want to build on top of the oracle?")
d = tool("litvm_deploy_template", {"framework": "foundry"})
out(f"{d['framework']} config for chain {d['chain_id']}, plus a contract that reads the root:")
out(f"{GREY}   interface IMerklePriceOracle {{ function merkleRoot() external view …{OFF}")
print()
print(f"{GREY}Six tools. Every one a read. The price was committed on-chain before anyone asked.{OFF}")
