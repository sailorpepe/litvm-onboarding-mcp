"""LitVM read-only tools for AI agents.

Four tools over MCP against LitecoinVM's LiteForge chain (4441) and the trading-card
price oracle deployed there. The one that matters proves a real card price against the
Merkle root committed on-chain, and has the contract confirm it over a live eth_call.

Hosted at https://onboard.the-undesirables.com/mcp — no install, no account, no keys.

NO WALLET IS EVER REQUIRED. Every tool is a read. This server holds no keys, signs
nothing, and sends nothing. There is no code path here that can move an asset.

Built by sailorpepe / The Undesirables LLC, the operator of the price oracle on LiteForge.
"""
import json
import os
import time
from datetime import datetime, timezone

import httpx
from eth_abi import encode as abi_encode
from fastmcp import FastMCP
from web3 import Web3

# ---------------------------------------------------------------------------
# network facts (docs.litvm.com + chainlist 4441, verified live 2026-09-08)
# ---------------------------------------------------------------------------
CHAIN_ID = 4441
CHAIN_NAME = "LitVM LiteForge Testnet"
RPC_HTTP = "https://liteforge.rpc.caldera.xyz/http"
RPC_WS = "wss://liteforge.rpc.caldera.xyz/ws"
EXPLORER = "https://liteforge.explorer.caldera.xyz"
FAUCET = "https://liteforge.hub.caldera.xyz"
DOCS = "https://docs.litvm.com"
GAS_SYMBOL = "zkLTC"
ORACLE = "https://oracle.the-undesirables.com"
UA = "litvm-onboard-mcp/1.0"   # no URL in the UA: the Caldera RPC answers 415 to it

# Live contracts on LiteForge. Ours first (all verified on the explorer);
# third-party entries are added as they are confirmed on-chain.
CONTRACTS = [
    {"name": "MerklePriceOracle", "address": "0x20A812309AD14aa39B59aE2791972dfe8dDDe80E",
     "operator": "The Undesirables", "what": "Daily Merkle root over 289K+ trading-card prices; verifyPrice()/verifyAndRecord() check a card's price against it",
     "abi": "https://github.com/sailorpepe/undesirables-x402-server/blob/main/MerklePriceOracle_abi.json"},
    {"name": "GradedPriceOracle", "address": "0x6cca6D7727525595D3A5A1197133086507b82f17",
     "operator": "The Undesirables", "what": "Merkle root over PSA/BGS/CGC graded-slab prices"},
    {"name": "TCGPriceOracleV2", "address": "0x697bF6AE96fb05a47106abd012C39855A16a720E",
     "operator": "The Undesirables", "what": "50 blue-chip card TWAP feeds, hourly"},
    {"name": "SoulPredictionOracle", "address": "0x5503D08D7D167eE23AcE818bff1a00eF77A76dBF",
     "operator": "The Undesirables", "what": "Weekly write-once roots of 4,444 AI souls' locked predictions"},
    {"name": "SoulResultsOracle", "address": "0x6f36dD393C399e7E739d4bb95091c42fEC3E5c6f",
     "operator": "The Undesirables", "what": "Write-once grading envelope: outcomes committed after maturity"},
    {"name": "PredictionRegistry", "address": "0x6C53bFcA4DfE2ed4B5852ce771e91B83A4f097b9",
     "operator": "The Undesirables", "what": "Forward-looking claims (fantasy lineups, forecasts) committed before they can mature"},
    {"name": "SportsStatsRegistryV2", "address": "0x9b681D78fC073ffca741ac613Fd28B1914A44Ae9",
     "operator": "The Undesirables", "what": "Daily write-once sports stat roots + the daily TCG price panel"},
    {"name": "GradingEscrow", "address": "0xe784d2AE4171De8f909eb638a60BE03B2341bB82",
     "operator": "The Undesirables", "what": "Pay-to-grade escrow for AI card grading"},
    {"name": "WeatherEdgeOracle", "address": "0x9955afC8AE25405ed9FcE66c23fa8E02eB3b6696",
     "operator": "The Undesirables", "what": "Hourly Merkle roots of 10-city NWS observations"},
]

MERKLE = Web3.to_checksum_address(CONTRACTS[0]["address"])
MERKLE_ABI = json.loads("""[
 {"inputs":[],"name":"merkleRoot","outputs":[{"type":"bytes32"}],"stateMutability":"view","type":"function"},
 {"inputs":[],"name":"lastRootUpdate","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"},
 {"inputs":[],"name":"totalProducts","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"},
 {"inputs":[],"name":"totalRootUpdates","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"},
 {"inputs":[],"name":"isRootFresh","outputs":[{"type":"bool"}],"stateMutability":"view","type":"function"},
 {"inputs":[{"type":"uint256","name":"_productId"},{"type":"uint256","name":"_categoryId"},{"type":"string","name":"_name"},{"type":"uint256","name":"_marketPrice"},{"type":"uint256","name":"_lowPrice"},{"type":"bytes32[]","name":"_proof"}],"name":"verifyPrice","outputs":[{"type":"bool"}],"stateMutability":"view","type":"function"},
 {"inputs":[{"type":"uint256","name":"_productId"},{"type":"uint256","name":"_categoryId"},{"type":"string","name":"_name"},{"type":"uint256","name":"_marketPrice"},{"type":"uint256","name":"_lowPrice"},{"type":"bytes32[]","name":"_proof"}],"name":"verifyAndRecord","outputs":[{"type":"bool"}],"stateMutability":"nonpayable","type":"function"}
]""")



def _w3() -> Web3:
    return Web3(Web3.HTTPProvider(RPC_HTTP, request_kwargs={"timeout": 20, "headers": {"User-Agent": UA, "Content-Type": "application/json"}}))



def _bad_address(value: str, field: str = "address") -> dict:
    """Errors an agent can act on: the constraint, a concrete example, and the next move."""
    return {
        "error": f"'{str(value)[:40]}' is not a valid EVM address for `{field}`.",
        "expected": "0x followed by 40 hex characters. Checksummed or all-lower-case both work.",
        "example": "0x742d35cC6634c0532925A3b844bc9E7595F0beB1",
        "next": "Ask the person for the address of a wallet they already control. Never generate "
                "one for them and never ask for a private key.",
    }


def _oracle(path: str, params: dict | None = None) -> dict:
    r = httpx.get(ORACLE + path, params=params, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    return r.json()


mcp = FastMCP(
    "LitVM Agent Onboarding",
    instructions=(
        "Read-only access to LitecoinVM's LiteForge chain (4441) and the trading-card price "
        "oracle deployed on it. litvm_verify_price is the one that matters: it proves a real "
        "card price against the Merkle root committed on-chain, and the contract confirms it "
        "over a live eth_call. litvm_network gives connection details, litvm_contracts lists "
        "what is deployed, litvm_deploy_template sets up a project that reads the oracle. "
        "NO WALLET, NO KEY, NO GAS — every tool here is a read. Nothing is ever signed or sent."
    ),
)


@mcp.tool(title="LitVM network details", annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": True})
def litvm_network() -> dict:
    """Chain 4441 connection details for LitVM LiteForge in one call: RPC (HTTP and WebSocket),
    explorer, faucet, gas token, the live block height and gas price, and a ready-to-paste
    wallet-network JSON object.

    START HERE. Every other tool assumes the caller already knows the chain id and RPC — this
    is where those come from. Takes no arguments.

    Use litvm_contracts instead when you want what is deployed ON the chain rather than how to
    reach it.

    Reads the chain over a public RPC and changes nothing. If the RPC is unreachable the call
    still succeeds and reports the failure inside the "live" field, so the static network facts
    stay usable offline.

    Called with no arguments: `litvm_network()`.
    """
    w3 = _w3()
    out = {
        "chain_id": CHAIN_ID, "name": CHAIN_NAME, "gas_token": GAS_SYMBOL,
        "rpc_http": RPC_HTTP, "rpc_ws": RPC_WS, "explorer": EXPLORER, "faucet": FAUCET, "docs": DOCS,
        "settlement": "Arbitrum Orbit rollup, BitcoinOS ZK proofs, Espresso shared sequencing (per litvm.com)",
        "wallet_add_network": {"chainId": hex(CHAIN_ID), "chainName": CHAIN_NAME,
                               "nativeCurrency": {"name": "zkLTC", "symbol": GAS_SYMBOL, "decimals": 18},
                               "rpcUrls": [RPC_HTTP], "blockExplorerUrls": [EXPLORER]},
        "warning": "Testnet only. Assets have no value; nothing here is a mainnet guarantee.",
    }
    try:
        out["live"] = {"block": w3.eth.block_number, "gas_price_wei": w3.eth.gas_price,
                       "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    except Exception as e:
        out["live"] = {"error": f"RPC unreachable: {str(e)[:100]}"}
    return out


@mcp.tool(title="Get testnet zkLTC", annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": True})
def litvm_fund(address: str) -> dict:
    """How to get testnet zkLTC for an address you already control, and whether it has any yet.

    Use this when someone wants to do anything on LiteForge that writes to the chain, since
    that costs gas. Writing is not required to read prices — litvm_verify_price needs no gas
    and no wallet at all.

    THIS TOOL CANNOT CLAIM FOR YOU AND HOLDS NO KEYS. The LiteForge faucet is a browser page
    with no API, so what you get back is the link and the exact steps for a person to follow
    in their own wallet. Nothing here is signed or sent.

    Read-only: one balance lookup on a public address. Sends nothing, stores nothing.

    Typical call: `litvm_fund(address="0x742d35cC6634c0532925A3b844bc9E7595F0beB1")`.

    Args:
        address: the EVM address that should receive testnet zkLTC. It must be a wallet the
            person already controls — never generate one for them, and never ask for a key.
    """
    try:
        a = Web3.to_checksum_address(address)
    except Exception:
        return _bad_address(address)
    bal = _w3().eth.get_balance(a)
    return {
        "address": a, "already_funded": bal > 0,
        "balance_zkltc": float(Web3.from_wei(bal, "ether")), "balance_wei": bal,
        "faucet": FAUCET,
        "steps": [
            f"Open {FAUCET} in a browser — the Caldera hub is LitVM's official testnet faucet.",
            "Connect the wallet that owns this address, or paste the address if the hub allows it.",
            "Click 'Get zkLTC'. One claim per address per cooldown window.",
            "Rate-limited (429)? Pause any VPN or proxy, switch region, or wait a few minutes.",
            "Then call litvm_status(address) — a balance above zero means it landed.",
        ],
        "note": ("Testnet only: zkLTC has no monetary value. One claim covers hundreds of "
                 "transactions. You keep your own wallet — this server never sees a key."),
    }


@mcp.tool(title="Check an address on LiteForge", annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": True})
def litvm_status(address: str) -> dict:
    """Has this address got testnet gas yet, and has it done anything on LiteForge?

    Use this to poll after someone claims from the faucet, and to confirm they are ready
    before walking them through anything that writes to the chain. Use litvm_fund for the
    claim steps themselves.

    Balances and transaction counts on this chain are public, so the address does not have
    to be one you control. Read-only: one balance query and one nonce query. Holds no keys.

    Typical call: `litvm_status(address="0x742d35cC6634c0532925A3b844bc9E7595F0beB1")`.

    Args:
        address: any EVM address, checksummed or lower-case.
    """
    try:
        a = Web3.to_checksum_address(address)
    except Exception:
        return _bad_address(address)
    w3 = _w3()
    bal = w3.eth.get_balance(a); nonce = w3.eth.get_transaction_count(a)
    funded = bal > 0
    return {
        "address": a, "funded": funded,
        "balance_zkltc": float(Web3.from_wei(bal, "ether")), "balance_wei": bal,
        "transactions_sent": nonce, "explorer": f"{EXPLORER}/address/{a}",
        "next_steps": ([f"Funded with {float(Web3.from_wei(bal, 'ether')):.4f} {GAS_SYMBOL} — "
                        "ready to use LiteForge."]
                       if funded else
                       ["No gas yet. Call litvm_fund for the faucet steps, then check again.",
                        "Reading prices needs no gas — litvm_verify_price works right now."]),
    }


@mcp.tool(title="LiteForge contract directory", annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": True})
def litvm_contracts() -> dict:
    """Directory of contracts live on LiteForge: name, address, operator, what each one does, an
    explorer link, and a bytecode check confirming each is really deployed right now.

    Use this to discover what an agent can call on this chain, or to confirm an address before
    interacting with it. Use litvm_network instead for connection details, and litvm_verify_price
    to actually exercise the price oracle.

    Currently lists the nine oracle and registry contracts operated by The Undesirables; it is
    not an exhaustive index of the chain. Read-only: one eth_getCode per contract. No arguments.

    Called with no arguments: `litvm_contracts()`.
    """
    w3 = _w3()
    items = []
    for c in CONTRACTS:
        row = dict(c); row["explorer"] = f"{EXPLORER}/address/{c['address']}"
        try:
            row["deployed"] = len(w3.eth.get_code(Web3.to_checksum_address(c["address"]))) > 0
        except Exception:
            row["deployed"] = None
        items.append(row)
    return {"chain_id": CHAIN_ID, "count": len(items), "contracts": items,
            "submit": "Operate a contract on LiteForge? Open an issue at github.com/sailorpepe/litvm-tcg-oracle-mcp to be listed."}


@mcp.tool(title="Verify a card price on-chain",
          annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": True})
def litvm_verify_price(card_name: str = "", product_id: int = 0) -> dict:
    """Prove a real trading-card price against the Merkle root committed to LiteForge. No
    wallet, no key, no gas — this is a read.

    Use this whenever you want a price you do not have to trust the API for. It returns the
    proof, the exact leaf fields the contract hashes, today's root from the API next to the
    root read live from the contract, and the boolean result of asking the contract itself
    via verifyPrice(). Called with no arguments it demonstrates itself on a real card.

    Use litvm_contracts instead to see what else is deployed on the chain, and litvm_network
    for connection details.

    Read-only: one HTTP call to the oracle and one eth_call. Writes nothing, anywhere.

    Only actively-priced products are in the tree, so catalog-only entries cannot be proven —
    that case returns a clear error rather than a false negative.

    Called bare — `litvm_verify_price()` — it proves a real card, read-only.

    Typical calls: `litvm_verify_price(card_name="Charizard")`
    · by id, skipping the search: `litvm_verify_price(product_id=246723)`

    Args:
        card_name: any card name, resolved to the single best match (e.g. "Charizard").
        product_id: a TCGplayer product id. Use it instead of card_name when you already
            have one — it skips the search and is exact.
    """
    pid = int(product_id) if product_id else 0
    if not pid:
        if not card_name:
            card_name = "Umbreon VMAX (Alternate Art Secret)"   # bare call = live demo
        hit = _oracle("/api/v1/search", {"query": card_name, "limit": 1})
        res = (hit.get("data") or {}).get("results") or []
        if not res:
            return {"error": f"No card matched '{card_name}' in the 456K-product catalog.",
                    "expected": "A name close to how the card is printed: 'Charizard', 'Black Lotus', 'Pikachu VMAX'.",
                    "example": 'litvm_verify_price(card_name="Charizard")',
                    "next": "Try a shorter or more common form of the name, or pass a product_id directly."}
        pid = int(res[0]["product_id"])
    pr = _oracle("/api/v1/merkle/proof", {"product_id": pid}).get("data") or {}
    ld = pr.get("leaf_data") or {}
    if not ld or "error" in ld or not ld.get("leaf_matches"):
        return {"error": f"Product {pid} has no verifiable entry in today's tree.",
                "expected": "An actively-priced product — only those are committed on-chain.",
                "example": 'litvm_verify_price(product_id=246723)',
                "next": "Catalog-only entries (no market price today) cannot be proven. Pick a priced card.",
                "leaf_data": ld}
    proof = [bytes.fromhex(h[2:]) for h in pr["proof"]]
    args = [int(ld["product_id"]), int(ld["category_id"]), str(ld["name"]),
            int(ld["market_price_cents"]), int(ld["low_price_cents"]), proof]
    w3 = _w3(); c = w3.eth.contract(address=MERKLE, abi=MERKLE_ABI)
    onchain_root = "0x" + c.functions.merkleRoot().call().hex()
    return {
        "product_id": pid, "card": ld["name"], "market_price_usd": ld["market_price_cents"] / 100,
        "data_date": pr.get("data_date"),
        "oracle_root": pr.get("root"), "onchain_root": onchain_root,
        "roots_match": str(pr.get("root", "")).lower() == onchain_root.lower(),
        "verifyPrice_eth_call": bool(c.functions.verifyPrice(*args).call()),
        "contract": MERKLE, "explorer": f"{EXPLORER}/address/{MERKLE}",
        "leaf_data": ld, "proof": pr["proof"],
        "what_this_proves": ("The oracle's root and the chain's root are the same value, and the "
                             "contract itself confirmed this card's price against it. The price was "
                             "committed on-chain before you asked. It does not prove the price is "
                             "correct — only that nobody changed it after the fact."),
    }


@mcp.tool(title="Deploy-to-LiteForge template", annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False})
def litvm_deploy_template(framework: str = "foundry") -> dict:
    """Copy-paste project setup for deploying your own contract to LiteForge, plus a ten-line
    Solidity consumer that reads this oracle's Merkle root.

    Use this when the goal is to ship a contract rather than call an existing one. Use
    litvm_contracts instead to find something already deployed that you can call today.

    Pure text generation: it touches neither the chain nor the network, takes no keys, and
    writes no files. The caller decides what to do with the config it returns.


    Typical calls: `litvm_deploy_template(framework="foundry")` or `(framework="hardhat")`.

    Args:
        framework: "foundry", "hardhat" or "remix". Any other value returns an error naming
            the three valid ones.
    
    """
    fw = framework.lower().strip()
    consumer = (
        "// SPDX-License-Identifier: MIT\npragma solidity ^0.8.20;\n\n"
        "interface IMerklePriceOracle {\n    function merkleRoot() external view returns (bytes32);\n"
        "    function lastRootUpdate() external view returns (uint256);\n"
        "    function verifyPrice(uint256 productId, uint256 categoryId, string calldata name,\n"
        "        uint256 marketPrice, uint256 lowPrice, bytes32[] calldata proof) external view returns (bool);\n}\n\n"
        "contract CardPriceConsumer {\n"
        f"    IMerklePriceOracle constant ORACLE = IMerklePriceOracle({MERKLE});\n"
        "    function todaysRoot() external view returns (bytes32, uint256) {\n"
        "        return (ORACLE.merkleRoot(), ORACLE.lastRootUpdate());\n    }\n"
        "    function isPriceReal(uint256 pid, uint256 cat, string calldata name, uint256 mkt, uint256 low, bytes32[] calldata proof)\n"
        "        external view returns (bool) { return ORACLE.verifyPrice(pid, cat, name, mkt, low, proof); }\n}\n"
    )
    cfg = {
        "foundry": {"foundry.toml": f"[profile.default]\nsrc = 'src'\nout = 'out'\n\n[rpc_endpoints]\nliteforge = \"{RPC_HTTP}\"\n",
                    "deploy": f"forge create src/CardPriceConsumer.sol:CardPriceConsumer --rpc-url {RPC_HTTP} --private-key $PK --legacy",
                    "verify_note": f"Explorer: {EXPLORER} (Blockscout-style; use --verifier blockscout --verifier-url {EXPLORER}/api if supported)"},
        "hardhat": {"hardhat.config.js (networks)": f"liteforge: {{ url: \"{RPC_HTTP}\", chainId: {CHAIN_ID}, accounts: [process.env.PK] }}",
                    "deploy": "npx hardhat run scripts/deploy.js --network liteforge"},
        "remix": {"steps": [f"Add the network to MetaMask: chainId {CHAIN_ID}, RPC {RPC_HTTP}, symbol {GAS_SYMBOL}, explorer {EXPLORER}",
                             "Remix → Deploy & Run → Environment: Injected Provider (MetaMask on LiteForge)", "Paste the consumer contract, compile 0.8.20+, Deploy"]},
    }
    if fw not in cfg:
        return {"error": f"Unknown framework '{framework}'.",
                "expected": "One of: foundry, hardhat, remix.",
                "example": 'litvm_deploy_template(framework="foundry")',
                "next": "Foundry is the shortest path on this chain — it deploys with no config file."}
    return {"framework": fw, "chain_id": CHAIN_ID, "config": cfg[fw], "consumer_contract": consumer,
            "oracle": MERKLE, "docs": f"{DOCS}/deploy-on-testnet"}




# ---------------------------------------------------------------------------
# PROMPTS — user-controlled, surfaced as slash commands in MCP clients.
# An onboarding server is the canonical case for these: the whole five-step
# flow becomes one command instead of five messages.
# ---------------------------------------------------------------------------

@mcp.prompt(title="Verify a card price on-chain")
def verify_a_card(card_name: str = "Charizard") -> str:
    """Prove one trading-card price against the Merkle root committed to LiteForge. No wallet."""
    return (
        f'Prove the price of "{card_name}" without trusting the API that served it.\n\n'
        "Call litvm_verify_price, then explain the result to me "
        "in plain language:\n"
        "- Is oracle_root identical to onchain_root, and what does it mean that they are?\n"
        "- What does leaf_matches tell me about the five price fields?\n"
        "- verifyPrice_eth_call is the contract's own answer — say what was asked and what it said.\n"
        "- Finally, say clearly what this does NOT prove: that the price is correct, only that it "
        "was committed on-chain before I asked.\n\n"
        "This is a read-only check. Do not ask me for a private key; nothing here needs one."
    )


@mcp.prompt(title="Build on LitVM")
def build_on_litvm(framework: str = "foundry") -> str:
    """Set up a project and write a contract that reads the LitVM price oracle."""
    return (
        f"I want to deploy a contract to LitVM LiteForge using {framework} that reads the price "
        "oracle.\n\n"
        "1. Call litvm_network for the chain id and RPC.\n"
        f"2. Call litvm_deploy_template with framework={framework} and show me the config and the "
        "consumer contract.\n"
        "3. Call litvm_contracts and tell me which contract my consumer will be reading, and what "
        "it holds.\n"
        "4. Tell me exactly what I still need before I can deploy: a funded key, and how to get "
        "testnet zkLTC.\n\n"
        "Do not ask me for a private key or offer to hold one."
    )


@mcp.prompt(title="Get me set up on LitVM")
def get_started_on_litvm(address: str = "") -> str:
    """Walk me onto LitecoinVM's LiteForge chain using a wallet I already control."""
    who = f"My address is {address}." if address else "Ask me for my address if you need one."
    return (
        "Help me get set up on LitVM LiteForge. " + who + "\n\n"
        "Work through this and tell me what you find:\n"
        "1. Call litvm_network and give me the chain id and the network details to add to my wallet.\n"
        "2. Call litvm_verify_price so I can see what the chain is actually for — this one needs "
        "no wallet and no gas, so do it even if I am not set up yet.\n"
        "3. If I want to do anything that writes to the chain, call litvm_status on my address. "
        "If it has no gas, call litvm_fund and give me the faucet steps, then stop and wait for "
        "me to say I have claimed.\n"
        "4. Once I say so, call litvm_status again to confirm it landed.\n\n"
        "I keep my own wallet throughout. Do not ask me for a private key, do not offer to hold "
        "one, and do not generate a wallet for me — none of these tools can sign or send anything."
    )


# ---------------------------------------------------------------------------
# RESOURCES — application-controlled reference data. Same facts the tools
# return, but cacheable and attachable as context without spending a tool call.
# ---------------------------------------------------------------------------

@mcp.resource("litvm://network", name="LitVM LiteForge network", mime_type="application/json")
def network_resource() -> str:
    """Chain 4441 connection facts: RPC, explorer, faucet, gas token, wallet config."""
    return json.dumps({
        "chain_id": CHAIN_ID, "name": CHAIN_NAME, "gas_token": GAS_SYMBOL,
        "rpc_http": RPC_HTTP, "rpc_ws": RPC_WS, "explorer": EXPLORER,
        "faucet": FAUCET, "docs": DOCS,
        "wallet_add_network": {"chainId": hex(CHAIN_ID), "chainName": CHAIN_NAME,
                               "nativeCurrency": {"name": "zkLTC", "symbol": GAS_SYMBOL, "decimals": 18},
                               "rpcUrls": [RPC_HTTP], "blockExplorerUrls": [EXPLORER]},
        "note": "Static facts only — call litvm_network for the live block and gas price.",
    }, indent=2)


@mcp.resource("litvm://contracts", name="LiteForge contract directory", mime_type="application/json")
def contracts_resource() -> str:
    """Every contract this server knows about on LiteForge, with addresses and purpose."""
    return json.dumps({
        "chain_id": CHAIN_ID, "count": len(CONTRACTS),
        "contracts": [{**c, "explorer": f"{EXPLORER}/address/{c['address']}"} for c in CONTRACTS],
        "note": "Call litvm_contracts to additionally confirm each address has bytecode right now.",
    }, indent=2)


@mcp.custom_route("/.well-known/mcp/server-card.json", methods=["GET"])
async def server_card(request):
    """Static description of this server for scanners that cannot or will not connect."""
    from starlette.responses import JSONResponse
    return JSONResponse({
        "serverInfo": {"name": "LitVM Agent Onboarding", "version": "1.1.0",
                       "websiteUrl": "https://onboard.the-undesirables.com"},
        "authentication": {"required": False, "schemes": []},
        "transport": {"type": "streamable-http", "url": "https://onboard.the-undesirables.com/mcp"},
        "tools": [{"name": t, "description": d} for t, d in [
            ("litvm_network", "Chain 4441 connection details: RPC, explorer, faucet, live block, wallet config."),
            ("litvm_contracts", "Directory of live LiteForge contracts, each bytecode-checked."),
            ("litvm_verify_price", "Prove a real card price against the on-chain Merkle root. Read-only."),
            ("litvm_deploy_template", "Foundry/Hardhat/Remix config for chain 4441 plus a consumer contract."),
        ]],
        "prompts": [{"name": n} for n in ("verify_a_card", "build_on_litvm")],
        "resources": [{"uri": u} for u in ("litvm://network", "litvm://contracts")],
    })


def main():
    host = os.environ.get("HOST", "127.0.0.1"); port = int(os.environ.get("PORT", "8413"))
    mcp.run(transport="http", host=host, port=port, path="/mcp")


if __name__ == "__main__":
    main()
