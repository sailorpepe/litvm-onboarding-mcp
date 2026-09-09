"""Meticulous audit of the LitVM onboarding MCP server.
Usage: audit_onboard.py <base_url>   e.g. http://127.0.0.1:8414/mcp
Exits non-zero if anything fails."""
import json, sys, re, httpx

URL = sys.argv[1]
H = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
sid = None
FAIL, WARN, OK = [], [], []


def post(body):
    global sid
    h = dict(H)
    if sid:
        h["Mcp-Session-Id"] = sid
    r = httpx.post(URL, json=body, headers=h, timeout=120)
    sid = r.headers.get("mcp-session-id") or sid
    d = [json.loads(l[5:]) for l in r.text.splitlines() if l.startswith("data:")]
    if not d:
        d = [r.json()] if r.text.strip() else [None]
    return d[-1]


def check(cond, label, detail=""):
    (OK if cond else FAIL).append(label + (f" — {detail}" if detail and not cond else ""))
    print(("  PASS  " if cond else "  FAIL  ") + label + (f"  [{detail}]" if detail and not cond else ""))


def warn(cond, label, detail=""):
    if cond:
        OK.append(label); print("  PASS  " + label)
    else:
        WARN.append(label + (f" — {detail}" if detail else "")); print("  WARN  " + label + (f"  [{detail}]" if detail else ""))


def call(name, args):
    r = post({"jsonrpc": "2.0", "id": 99, "method": "tools/call",
              "params": {"name": name, "arguments": args}})
    if "error" in r:
        return {"__protocol_error__": r["error"]}
    res = r["result"]
    if res.get("isError"):
        return {"__tool_error__": res["content"][0]["text"][:200]}
    txt = res["content"][0]["text"] if res.get("content") else json.dumps(res.get("structuredContent"))
    try:
        return json.loads(txt)
    except Exception:
        return {"__raw__": txt[:300]}


print(f"\n=== AUDIT {URL} ===\n")

# ---------------------------------------------------------------- 1. handshake
init = post({"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                        "clientInfo": {"name": "audit", "version": "1"}}})
post({"jsonrpc": "2.0", "method": "notifications/initialized"})
caps = init["result"]["capabilities"]
print("1. HANDSHAKE")
check(init["result"]["serverInfo"]["name"] == "LitVM Agent Onboarding", "server name correct")
check("tools" in caps, "tools capability declared")
check("prompts" in caps, "prompts capability declared")
check("resources" in caps, "resources capability declared")

# ------------------------------------------------------------------- 2. tools
print("\n2. TOOLS — inventory, annotations, TDQS description quality")
tools = post({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})["result"]["tools"]
EXPECTED = {"litvm_network", "litvm_status", "litvm_fund", "litvm_contracts",
            "litvm_verify_price", "litvm_deploy_template"}
check({t["name"] for t in tools} == EXPECTED, "exactly the 6 expected tools",
      str({t["name"] for t in tools} ^ EXPECTED))
WRITERS = set()   # nothing writes any more
for t in sorted(tools, key=lambda x: x["name"]):
    n, d, a = t["name"], t.get("description", ""), t.get("annotations") or {}
    check(bool(a), f"{n}: has annotations")
    check("readOnlyHint" in a, f"{n}: declares readOnlyHint")
    expected_ro = n not in WRITERS
    check(a.get("readOnlyHint") is expected_ro,
          f"{n}: readOnlyHint={expected_ro} (honest about the ledger)", str(a.get("readOnlyHint")))
    check(bool(t.get("title") or a.get("title")), f"{n}: has a display title")
    check(bool(t.get("outputSchema")), f"{n}: has an output schema")
    # TDQS: usage guidelines — does it say WHEN to use this vs alternatives?
    check(bool(re.search(r"\b(use this|use it|start here|use litvm_\w+ instead|instead of|rather than)\b", d, re.I)),
          f"{n}: description says WHEN to use it (TDQS 20%)")
    # TDQS: disambiguation — does it name a sibling tool?
    others = [o["name"] for o in tools if o["name"] != n]
    check(any(o in d for o in others), f"{n}: names a sibling tool (disambiguation)")
    # TDQS: behavioral transparency
    check(bool(re.search(r"read-only|records nothing|side effect|never sign|stores nothing|writes no files|changes nothing", d, re.I)),
          f"{n}: discloses side effects (TDQS 20%)")
    # Measured: examples in the definition took parameter handling 72% -> 90%
    check(f"`{n}(" in d, f"{n}: description carries a call example")
    # TDQS: conciseness — front-loaded, sane size
    warn(200 <= len(d) <= 1800, f"{n}: description length sane ({len(d)})", f"{len(d)} chars")
    params = list((t.get("inputSchema") or {}).get("properties") or {})
    if params:
        props = (t.get("inputSchema") or {}).get("properties") or {}
        undocumented = [q for q in params if not (props.get(q, {}).get("description") or q in d)]
        check(not undocumented, f"{n}: documents every parameter ({', '.join(params)})", "missing: " + ",".join(undocumented))

# ----------------------------------------------------------------- 3. prompts
print("\n3. PROMPTS")
pr = post({"jsonrpc": "2.0", "id": 3, "method": "prompts/list", "params": {}})
check("error" not in pr, "prompts/list works", str(pr.get("error")))
prompts = pr.get("result", {}).get("prompts", [])
check(len(prompts) == 3, "3 prompts registered", str(len(prompts)))
for p in prompts:
    check(bool(p.get("description")), f"prompt {p['name']}: has a description")
    got = post({"jsonrpc": "2.0", "id": 4, "method": "prompts/get",
                "params": {"name": p["name"], "arguments": {}}})
    check("error" not in got, f"prompt {p['name']}: renders with no arguments", str(got.get("error")))
    if "result" in got:
        text = " ".join(m["content"]["text"] for m in got["result"]["messages"])
        check(len(text) > 200, f"prompt {p['name']}: produces substantial text ({len(text)} chars)")
        check("litvm_" in text, f"prompt {p['name']}: references real tools")
        check("private key" in text.lower(), f"prompt {p['name']}: warns against key handling")

# --------------------------------------------------------------- 4. resources
print("\n4. RESOURCES")
rs = post({"jsonrpc": "2.0", "id": 5, "method": "resources/list", "params": {}})
check("error" not in rs, "resources/list works", str(rs.get("error")))
resources = rs.get("result", {}).get("resources", [])
check(len(resources) == 2, "2 resources registered", str(len(resources)))
for r in resources:
    got = post({"jsonrpc": "2.0", "id": 6, "method": "resources/read", "params": {"uri": r["uri"]}})
    check("error" not in got, f"resource {r['uri']}: readable", str(got.get("error")))
    if "result" in got:
        body = got["result"]["contents"][0].get("text", "")
        try:
            parsed = json.loads(body); check(True, f"resource {r['uri']}: valid JSON ({len(body)} bytes)")
            if "network" in r["uri"]:
                check(parsed.get("chain_id") == 4441, "network resource: chain id 4441")
            if "contracts" in r["uri"]:
                check(parsed.get("count") == 9, "contracts resource: 9 contracts")
        except Exception as e:
            check(False, f"resource {r['uri']}: valid JSON", str(e))

# ------------------------------------------------------- 5. every tool, live
print("\n5. LIVE TOOL CALLS")
A = "0x742d35cC6634c0532925A3b844bc9E7595F0beB1"
n = call("litvm_network", {})
check(isinstance(n.get("live", {}).get("block"), int), "litvm_network: live block from RPC", str(n.get("live")))
check(n.get("chain_id") == 4441, "litvm_network: chain id 4441")
check(n.get("wallet_add_network", {}).get("chainId") == "0x1159", "litvm_network: hex chain id correct")

co = call("litvm_contracts", {})
check(co.get("count") == 9, "litvm_contracts: 9 contracts")
check(all(c.get("deployed") for c in co.get("contracts", [])), "litvm_contracts: all 9 confirmed deployed on-chain")

fp = call("litvm_verify_price", {"product_id": 246723})
check(fp.get("roots_match") is True, "litvm_verify_price: oracle root == on-chain root", json.dumps(fp)[:160])
check(fp.get("verifyPrice_eth_call") is True, "litvm_verify_price: contract verifyPrice returned true")
check(fp.get("leaf_data", {}).get("leaf_matches") is True, "litvm_verify_price: leaf fields hash to the leaf")
check(len(fp.get("proof", [])) > 5, "litvm_verify_price: real proof array")
check("unsigned_transaction" not in fp and "from_address" not in json.dumps(fp),
      "litvm_verify_price: builds NO transaction and takes no sender")
check(bool(fp.get("what_this_proves")), "litvm_verify_price: states what it does and does not prove")
demo = call("litvm_verify_price", {})
check(demo.get("verifyPrice_eth_call") is True, "litvm_verify_price: bare call self-demos (directory probes hit this)")

st = call("litvm_status", {"address": A})
check(st.get("balance_zkltc") is not None and st.get("balance_wei") is not None,
      "litvm_status: balance in both zkLTC and raw wei")
check(isinstance(st.get("transactions_sent"), int), "litvm_status: returns a nonce")
check(isinstance(st.get("next_steps"), list) and st["next_steps"], "litvm_status: returns next_steps")

fu = call("litvm_fund", {"address": A})
check(len(fu.get("steps", [])) == 5, "litvm_fund: 5 faucet steps")
check("429" in json.dumps(fu), "litvm_fund: documents the rate-limit workaround")
check("never sees a key" in json.dumps(fu), "litvm_fund: states it holds no key")

for fw in ("foundry", "hardhat", "remix"):
    d = call("litvm_deploy_template", {"framework": fw})
    check("consumer_contract" in d and d.get("framework") == fw, f"litvm_deploy_template: {fw} works")
bad = call("litvm_deploy_template", {"framework": "truffle"})
check("error" in bad and "foundry" in json.dumps(bad), "litvm_deploy_template: bad framework errors helpfully")

# the whole safety claim, asserted rather than assumed
blob = json.dumps([call(t, a) for t, a in [
    ("litvm_network", {}), ("litvm_contracts", {}), ("litvm_verify_price", {}),
    ("litvm_status", {"address": A}), ("litvm_fund", {"address": A}),
    ("litvm_deploy_template", {"framework": "foundry"})]])
check(not any(k in blob for k in ("privateKey", "private_key", "mnemonic", "rawTransaction",
                                  "unsigned_transaction", "signed")),
      "NO tool response contains key material or a transaction to sign")
check(all((t.get("annotations") or {}).get("readOnlyHint") is True for t in tools),
      "every tool is annotated readOnlyHint=true")

# ------------------------------------------------------------ 6. error paths
print("\n6. ERROR HANDLING")
for name, args, label in [
    ("litvm_status", {"address": "not-an-address"}, "litvm_status: invalid address"),
    ("litvm_fund", {"address": "0x123"}, "litvm_fund: too-short address"),
    ("litvm_verify_price", {"card_name": "zzzz-no-such-card-zzzz"}, "litvm_verify_price: unknown card"),
]:
    r = call(name, args)
    check("error" in r or "__tool_error__" in r, label + " returns a clean error", json.dumps(r)[:120])
    if "error" in r:
        check(len(r["error"]) > 10 and not r["error"].startswith("Traceback"),
              label + ": error is human-readable")
        check(bool(r.get("expected")), label + ": error states what was expected")
        check(bool(r.get("example")), label + ": error carries a concrete example")
        check(bool(r.get("next")), label + ": error names the next action")

print("\n" + "=" * 62)
print(f"PASS {len(OK)}   WARN {len(WARN)}   FAIL {len(FAIL)}")
if WARN:
    print("\nWARNINGS:"); [print("  - " + w) for w in WARN]
if FAIL:
    print("\nFAILURES:"); [print("  - " + f) for f in FAIL]
sys.exit(1 if FAIL else 0)
