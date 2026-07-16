#!/usr/bin/env python3
"""fetch_erc8004_agentids.py — Lee los agentId minados de las 3 tx en Base.
Read-only: consulta eth_getTransactionReceipt en el RPC publico de Base.
No requiere wallet ni key.
Uso:
  env -i PATH="/tmp/ethvenv/bin:/usr/bin:/bin" PYTHONPATH="" python3 fetch_erc8004_agentids.py
"""
import json
import urllib.request
from eth_utils import keccak

BASE_RPC = "https://mainnet.base.org"
REGISTRY = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"

TXS = {
    "VeraData":   "0x48cca29d21e53f89924586ea707ddd7d8534b33d5d5266293be32b26d5617fb5",
    "Intelica":   "0xe8019d341b7a2524567f251dd7c170bd7f6af47c17619bf590194202d6252f1a",
    "TrustBoost": "0x25802faafd72a9bfff7c1cf577a68d11428a3b116dc62c2a51daf396ddbb3b8f",
}

# topic0 de Registered(uint256,string,address) = keccak256("Registered(uint256,string,address)")
TOPIC_REGISTERED = "0x" + keccak(text="Registered(uint256,string,address)").hex()


def _rpc(method, params):
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(BASE_RPC, data=payload,
                                 headers={"Content-Type": "application/json", "User-Agent": "fetch/1"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def main():
    for name, tx in TXS.items():
        res = _rpc("eth_getTransactionReceipt", [tx])
        r = res.get("result")
        if not r:
            print(f"  [{name}] receipt pendiente o no encontrado (tx={tx[:12]}...)")
            continue
        for log in r.get("logs", []):
            if log.get("address", "").lower() == REGISTRY.lower() and TOPIC_REGISTERED in log.get("topics", []):
                # topic1 = agentId (uint256, 32 bytes)
                agent_id = int(log["topics"][1], 16)
                print(f"  [{name}] agentId = {agent_id}")
                print(f"           Basescan: https://basescan.org/token/{REGISTRY}?a={agent_id}")
                break
        else:
            print(f"  [{name}] sin evento Registered en receipt (tx={tx[:12]}...)")


if __name__ == "__main__":
    main()
