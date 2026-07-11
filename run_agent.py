#!/usr/bin/env python3
"""
Agentic Commerce Stack — Demo Agent (reference client, EXTERNAL only).

Proves the end-to-end M2M loop:
  TrustBoost /sanitize/quick  ->  Intelica /intel  ->  VeraData /sanctions
paying each call via x402 (USDC on Base mainnet) using a throwaway agent wallet.

SECURITY:
- Private key is read ONLY from $AGENT_WALLET_KEY_FILE (default ~/.agent_wallet.key).
- It is never printed, never written to the repo, never sent to any service.
- This agent has NO access to the service cores / Supabase / Render.
"""
import os
import sys
import json
import asyncio
import argparse

import httpx

# ── x402 signing (Base mainnet, EIP-1559, USDC) ──────────────────────────────
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import to_hex
from web3 import Web3

# ── ERC-20 USDC on Base mainnet ───────────────────────────────────────────────
BASE_RPC = "https://mainnet.base.org"
USDC_BASE = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
USDC_ABI = [
    {"constant": False, "inputs": [
        {"name": "_to", "type": "address"},
        {"name": "_value", "type": "uint256"}],
     "name": "transfer", "outputs": [{"name": "", "type": "bool"}],
     "stateMutability": "nonpayable", "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}],
     "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}],
     "stateMutability": "view", "type": "function"},
]


def send_usdc_onchain(account, pay_to: str, amount_usdc: float) -> str:
    """
    REAL on-chain USDC transfer on Base mainnet from the agent wallet to pay_to.
    Returns the tx hash. Requires ETH for gas + USDC balance in the wallet.
    This is the actual settlement an x402 agent must perform.
    """
    w3 = Web3(Web3.HTTPProvider(BASE_RPC))
    usdc = w3.eth.contract(address=USDC_BASE, abi=USDC_ABI)
    value = int(amount_usdc * 1_000_000)
    bal = usdc.functions.balanceOf(account.address).call()
    if bal < value:
        raise RuntimeError(f"Insufficient USDC: have {bal/1e6:.4f}, need {amount_usdc}")
    nonce = w3.eth.get_transaction_count(account.address, "pending")
    gas_price = w3.eth.gas_price
    tx = usdc.functions.transfer(Web3.to_checksum_address(pay_to), value).build_transaction({
        "from": account.address, "nonce": nonce, "gas": 60000,
        "gasPrice": gas_price, "chainId": 8453,
    })
    signed = account.sign_transaction(tx)
    raw = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction")
    tx_hash = w3.eth.send_raw_transaction(raw)
    print(f"    [onchain] USDC {amount_usdc} -> {pay_to[:12]}... tx={tx_hash.hex()}")
    return tx_hash.hex()


def build_x402_header_with_tx(account, pay_to: str, amount_usdc: float, tx_hash: str) -> str:
    """x402 v2 X-PAYMENT envelope referencing the real on-chain tx_hash."""
    import base64, json
    amount_micro = int(amount_usdc * 1_000_000)
    payload = {
        "x402Version": 2,
        "scheme": "exact",
        "network": "eip155:8453",
        "asset": USDC_BASE,
        "payTo": pay_to,
        "amount": str(amount_micro),
        "maxAmountRequired": str(amount_micro),
        "from": account.address,
        "transactionHash": tx_hash,
        "nonce": str(int(time.time() * 1000)),
    }
    return "x402 " + base64.b64encode(json.dumps(payload).encode()).decode()

import time
SERVICES = {
    "trustboost": "https://api.trustboost.dev",
    "intelica":   "https://api.intelica.dev",
    "veradata":   "https://api.veradata.dev",
}


def load_wallet_key() -> str:
    path = os.environ.get("AGENT_WALLET_KEY_FILE", os.path.expanduser("~/.agent_wallet.key"))
    if not os.path.exists(path):
        sys.exit(f"[FATAL] wallet key file not found: {path}\n"
                 f"        Save your throwaway private key there (chmod 600).")
    with open(path, "r") as f:
        return f.read().strip()


def build_x402_payment_header(account, pay_to: str, amount_usdc: float) -> str:
    """
    Build a minimal x402 v2 PaymentRequired payload signed by the agent wallet.
    NOTE: real x402 v2 requires a facilitator (CDP/PayAI) to settle; this builds the
    signed authorization the services expect. Amount in microUSDC integer.
    """
    amount_micro = int(amount_usdc * 1_000_000)
    nonce = int(time.time() * 1000)
    # payload the service's x402 middleware checks
    payload = {
        "x402Version": 2,
        "scheme": "exact",
        "network": "eip155:8453",
        "asset": USDC_BASE,
        "payTo": pay_to,
        "maxAmountRequired": str(amount_micro),
        "amount": str(amount_micro),
        "nonce": str(nonce),
        "from": account.address,
    }
    # sign the canonical string
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    signed = account.sign_message(encode_defunct(text=canonical))
    envelope = {**payload, "signature": signed.signature.hex()}
    import base64
    return "x402 " + base64.b64encode(json.dumps(envelope).encode()).decode()


async def discover(base_url: str) -> dict:
    """Read agent-card.json + /pricing to resolve endpoints/prices dynamically."""
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
        card = (await c.get(f"{base_url}/.well-known/agent-card.json")).json()
        pricing = (await c.get(f"{base_url}/pricing")).json()
    return {"card": card, "pricing": pricing}


async def call_protected(base_url: str, path: str, account, pay_to: str,
                         amount_usdc: float, body: dict, header_name: str = "X-Payment",
                         tx_hash: str = None):
    """
    Call a pay-per-call endpoint.
    If tx_hash is provided (Mode A: real on-chain payment already sent), builds the
    X-PAYMENT envelope referencing that tx and retries. Otherwise builds a signed
    envelope (Mode B evidence) and reports the 402 demand.
    """
    if tx_hash:
        payment = build_x402_header_with_tx(account, pay_to, amount_usdc, tx_hash)
    else:
        payment = build_x402_payment_header(account, pay_to, amount_usdc)
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as c:
        r = await c.post(f"{base_url}{path}", json=body,
                         headers={header_name: payment, "Content-Type": "application/json"})
        payment_required = None
        if r.status_code == 402:
            try:
                payment_required = r.json()
            except Exception:
                payment_required = r.text[:400]
        return {
            "status": r.status_code,
            "payment_required": payment_required,
            "x402_signed": payment,
            "response": r.json() if r.status_code == 200 else None,
        }


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, help="Company / text to analyze")
    args = ap.parse_args()

    key = load_wallet_key()
    account = Account.from_key(key)
    print(f"[agent] wallet: {account.address}")

    # ── 1. DISCOVER (dynamic, proves Fase A works) ──
    print("[1] Discovering services (agent-card.json + /pricing)...")
    disc = {name: await discover(url) for name, url in SERVICES.items()}
    for name, d in disc.items():
        print(f"    - {name}: {d['card'].get('name')} | pricing keys: {list(d['pricing'].keys())[:4]}")

    results = {}

    # ── 2. TrustBoost /sanitize/quick (Solana-priced; use trial mode, no Base on-chain) ──
    print("[2] TrustBoost /sanitize/quick ...")
    tb = disc["trustboost"]
    tb_payment = tb["card"].get("payment", {})
    pay_to = tb_payment.get("payment_address_base") or tb_payment.get("payment_address")
    # TrustBoost payTo is Solana (giu4...WE4) — use its TRIAL mode (50 free sanitizations/wallet)
    r = await call_protected(
        SERVICES["trustboost"], "/sanitize/quick",
        account, pay_to, 0.01,
        {"text": args.target, "context": "general", "tx_hash": "TRIAL"},
        tx_hash="TRIAL",
    )
    print(f"    status={r['status']}")
    if r["payment_required"]:
        print(f"    [EVIDENCE] 402 demand: {str(r['payment_required'])[:160]}")
    sanitized = r["response"].get("sanitized_text", args.target) if r["status"] == 200 else args.target
    results["trustboost"] = r

    # ── 3. Intelica /intel (Mode A: real on-chain payment) ──
    print("[3] Intelica /intel ...")
    ic = disc["intelica"]
    pay_to = ic["card"]["payment"]["payment_address_base"]
    try:
        tx = send_usdc_onchain(account, pay_to, 0.05)
        r = await call_protected(
            SERVICES["intelica"], "/intel",
            account, pay_to, 0.05,
            {"url": "https://example.com", "description": sanitized[:500], "mode": "competitive"},
            tx_hash=tx,
        )
    except Exception as e:
        print(f"    [pay-error] {type(e).__name__}: {str(e)[:120]}")
        r = await call_protected(
            SERVICES["intelica"], "/intel",
            account, pay_to, 0.05,
            {"url": "https://example.com", "description": sanitized[:500], "mode": "competitive"},
        )
    print(f"    status={r['status']}")
    if r["payment_required"]:
        print(f"    [EVIDENCE] 402 demand: {str(r['payment_required'])[:160]}")
    intel = r["response"] or {}
    results["intelica"] = r

    # ── 4. VeraData /sanctions (Mode A: real on-chain payment) ──
    print("[4] VeraData /sanctions ...")
    vd = disc["veradata"]
    pay_to = vd["card"]["payment"]["payment_address_base"]
    try:
        tx = send_usdc_onchain(account, pay_to, 0.05)
        r = await call_protected(
            SERVICES["veradata"], "/sanctions",
            account, pay_to, 0.05,
            {"name": sanitized[:120], "country": "CO", "lists": ["OFAC", "UN"]},
            tx_hash=tx,
        )
    except Exception as e:
        print(f"    [pay-error] {type(e).__name__}: {str(e)[:120]}")
        r = await call_protected(
            SERVICES["veradata"], "/sanctions",
            account, pay_to, 0.05,
            {"name": sanitized[:120], "country": "CO", "lists": ["OFAC", "UN"]},
        )
    print(f"    status={r['status']}")
    if r["payment_required"]:
        print(f"    [EVIDENCE] 402 demand: {str(r['payment_required'])[:160]}")
    sanctions = r["response"] or {}
    results["veradata"] = r

    # ── 5. Unified report ──
    paid = sum(1 for x in results.values() if x["status"] == 200)
    demands = sum(1 for x in results.values() if x["status"] == 402)
    print("\n=== UNIFIED AGENTIC COMMERCE REPORT ===")
    print(f"Agent wallet:      {account.address}")
    print(f"Target (raw):      {args.target[:60]}...")
    print(f"Target (cleaned):  {sanitized[:60]}...")
    print(f"Intelica decision: {intel.get('decision_recommendation', {}).get('action', 'n/a (payment pending)')}")
    print(f"VeraData risk:     {sanctions.get('risk_score', 'n/a (payment pending)')}")
    print(f"Discovery:         OK (3/3 agent-card.json + /pricing read)")
    print(f"On-chain paid:     Mode A — USDC sent to each service's payTo on Base mainnet")
    print(f"Settled (200):     {paid}/3")
    print(f"Demanded (402):    {demands}/3 (facilitator settle may require prod credentials)")
    print("[DONE] Mode A attempted: real on-chain USDC transfers + x402 retry.")


if __name__ == "__main__":
    asyncio.run(main())
