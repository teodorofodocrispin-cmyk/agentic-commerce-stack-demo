#!/usr/bin/env python3
"""
mine_erc8004_agents.py (v2 — flujo correcto ERC-8004 reference impl)
Minar 3 agents en el Identity Registry de Base (0x8004A169...).

FLUJO: register() mina el agentId (sin URI), luego setAgentURI(agentId, uri)
le asigna el agent-card.json. Son 2 tx por servicio (6 total).

SEGURIDAD: lee private key de ~/.base_wallet_key (chmod 600). NUNCA en chat.
Requiere eth_account en /tmp/ethvenv y ETH en Base para gas.
"""
import json
import urllib.request
from eth_account import Account
from eth_utils import keccak

REGISTRY = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
BASE_RPC = "https://mainnet.base.org"
CHAIN_ID = 8453

SEL_REGISTER = "0x" + keccak(text="register()").hex()[:8]            # 0x1aa3a008
SEL_SETURI = "0x" + keccak(text="setAgentURI(uint256,string)").hex()[:8]  # 0x0af28bd3

SERVICES = [
    ("VeraData",   "https://api.veradata.dev/.well-known/agent-card.json"),
    ("Intelica",   "https://api.intelica.dev/.well-known/agent-card.json"),
    ("TrustBoost", "https://api.trustboost.dev/.well-known/erc8004-agent.json"),
]


def _rpc(method, params):
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(BASE_RPC, data=payload,
                                 headers={"Content-Type": "application/json", "User-Agent": "mine/2"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def _encode_string(s: str) -> str:
    b = s.encode()
    pad = (32 - (len(b) % 32)) % 32
    return (32).to_bytes(32, "big").hex() + len(b).to_bytes(32, "big").hex() + b.hex() + (b"\x00" * pad).hex()


def _send(acct, to, data_hex, nonce, gas_price, gas):
    tx = {"nonce": nonce, "to": to, "value": 0, "gasPrice": gas_price,
          "gas": gas, "data": "0x" + data_hex, "chainId": CHAIN_ID}
    signed = acct.sign_transaction(tx)
    raw = signed.raw_transaction.hex() if hasattr(signed, "raw_transaction") else signed.rawTransaction.hex()
    res = _rpc("eth_sendRawTransaction", ["0x" + raw])
    if "error" in res:
        return None, res["error"]
    return res.get("result"), None


def _get_agentid_from_receipt(tx_hash):
    r = _rpc("eth_getTransactionReceipt", [tx_hash])
    rec = r.get("result")
    if not rec:
        return None
    topic = "0x" + keccak(text="Registered(uint256,string,address)").hex()
    for log in rec.get("logs", []):
        if log.get("address", "").lower() == REGISTRY.lower() and topic in log.get("topics", []):
            return int(log["topics"][1], 16)
    return None


def main():
    try:
        with open("/Users/ivargarces/.base_wallet_key") as f:
            pk = f.read().strip()
    except FileNotFoundError:
        print("ERROR: crea ~/.base_wallet_key con tu private key (chmod 600) primero.")
        return
    acct = Account.from_key(pk)
    print(f"Minando desde: {acct.address}")
    nonce = int(_rpc("eth_getTransactionCount", [acct.address, "pending"])["result"], 16)
    gas_price = int(_rpc("eth_gasPrice", [])["result"], 16)

    for name, uri in SERVICES:
        # Paso 1: register()
        tx1, err1 = _send(acct, REGISTRY, SEL_REGISTER[2:], nonce, gas_price, 200000)
        if err1:
            print(f"  [{name}] register ERROR: {err1}")
            nonce += 1
            continue
        print(f"  [{name}] register tx={tx1}")
        nonce += 1
        # esperar receipt para sacar agentId
        agent_id = None
        for _ in range(10):
            agent_id = _get_agentid_from_receipt(tx1)
            if agent_id is not None:
                break
            import time; time.sleep(2)
        if agent_id is None:
            print(f"  [{name}] no se obtuvo agentId del receipt. Revisa tx en Basescan.")
            continue
        print(f"  [{name}] agentId={agent_id}")
        # Paso 2: setAgentURI(agentId, uri)
        data2 = SEL_SETURI[2:] + agent_id.to_bytes(32, "big").hex() + _encode_string(uri)
        tx2, err2 = _send(acct, REGISTRY, data2, nonce, gas_price, 200000)
        if err2:
            print(f"  [{name}] setAgentURI ERROR: {err2}")
            nonce += 1
            continue
        print(f"  [{name}] setAgentURI tx={tx2} -> {uri}")
        nonce += 1
    print("Listo. Verifica los agentId en Basescan: cada register() mino un token ERC-721.")


if __name__ == "__main__":
    main()
