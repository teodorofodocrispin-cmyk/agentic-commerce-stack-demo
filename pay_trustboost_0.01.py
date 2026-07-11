"""
pay_trustboost_0.01.py — Paga 0.01 USDC a WALLET_BASE en Base mainnet y arma el
X-Payment header para el smoke test de TrustBoost /sanitize (modo micropago per-call).

Reutiliza el patron del demo agent: lee la wallet desde AGENT_WALLET_KEY_FILE
(~/.agent_wallet.key, chmod 600), firma ERC-20 transfer USDC, espera confirmacion,
e imprime el tx_hash + el header X-Payment listo para pegar en el curl.

Uso:
  export AGENT_WALLET_KEY_FILE=~/.agent_wallet.key
  python3 pay_trustboost_0.01.py

Luego copia el bloque del curl que imprime al final.
"""
import os
import sys
import json
import time
import base64

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware  # Base is POA-like for extraData
from eth_account import Account

# ── Constantes (deben coincidir con TrustBoost main.py) ──────────────────────
WALLET_BASE = Web3.to_checksum_address("0xCf1d31020A7915421f6d66B9835Dcb6f422337E7")
USDC_BASE = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
BASE_RPC = "https://mainnet.base.org"
AMOUNT_USDC = 0.01
AMOUNT_MICRO = int(AMOUNT_USDC * 1_000_000)  # USDC tiene 6 decimales

# Minimal ERC-20 ABI (transfer + allowance + balanceOf)
ERC20_ABI = [
    {"constant": False, "inputs": [{"name": "to", "type": "address"},
                                    {"name": "value", "type": "uint256"}],
     "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "owner", "type": "address"}],
     "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
]


def load_account():
    keyfile = os.environ.get("AGENT_WALLET_KEY_FILE", os.path.expanduser("~/.agent_wallet.key"))
    if not os.path.exists(keyfile):
        print(f"[ERR] No wallet key en {keyfile}. Set AGENT_WALLET_KEY_FILE.")
        sys.exit(1)
    with open(keyfile) as f:
        key = f.read().strip()
    if not key.startswith("0x"):
        key = "0x" + key
    return Account.from_key(key)


def build_x402_header(tx_hash: str, payer: str) -> str:
    payload = {
        "x402Version": 2,
        "scheme": "exact",
        "network": "eip155:8453",
        "asset": USDC_BASE,
        "payTo": WALLET_BASE,
        "amount": str(AMOUNT_MICRO),
        "maxAmountRequired": str(AMOUNT_MICRO),
        "from": payer,
        "transactionHash": tx_hash,
        "nonce": "1",
    }
    return "x402 " + base64.b64encode(json.dumps(payload).encode()).decode()


def main():
    w3 = Web3(Web3.HTTPProvider(BASE_RPC))
    try:
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    except Exception:
        pass
    if not w3.is_connected():
        print("[ERR] No conecta a Base RPC")
        sys.exit(1)

    acct = load_account()
    payer = acct.address
    print(f"Payer: {payer}")

    usdc = w3.eth.contract(address=USDC_BASE, abi=ERC20_ABI)
    bal = usdc.functions.balanceOf(payer).call()
    print(f"USDC balance: {bal / 1e6:.4f}")
    if bal < AMOUNT_MICRO:
        print(f"[ERR] Saldo insuficiente ({bal/1e6:.4f} < {AMOUNT_USDC})")
        sys.exit(1)

    eth_bal = w3.eth.get_balance(payer)
    if eth_bal < w3.to_wei("0.0005", "ether"):
        print(f"[ERR] ETH para gas insuficiente: {w3.from_wei(eth_bal,'ether'):.6f} ETH")
        sys.exit(1)

    nonce = w3.eth.get_transaction_count(payer)
    tx = usdc.functions.transfer(WALLET_BASE, AMOUNT_MICRO).build_transaction({
        "from": payer,
        "nonce": nonce,
        "gas": 80_000,
        "gasPrice": w3.to_wei("0.05", "gwei"),
        "chainId": 8453,
    })
    signed = acct.sign_transaction(tx)
    raw = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction")
    tx_hash = w3.eth.send_raw_transaction(raw)
    print(f"Enviado: {tx_hash.hex()}")
    print("Esperando confirmacion (hasta 60s)...")
    try:
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    except Exception as e:
        print(f"[WARN] Timeout esperando recibo: {e}. El tx puede tardar; revisa en basescan.")
        receipt = None
    if receipt and receipt["status"] != 1:
        print("[ERR] Tx revertido")
        sys.exit(1)

    header = build_x402_header(tx_hash.hex(), payer)
    print("\n=== LISTO ===")
    print(f"tx_hash: {tx_hash.hex()}")

    # Smoke test automatico: ejecuta el curl contra la URL directa de Render
    # (sin Cloudflare) para evitar truncado por copy/paste del header largo.
    import subprocess
    SANITIZE_URL = "https://trustboost-api.onrender.com/sanitize"
    payload = '{"text":"mi email es juan@empresa.com y mi tel 571234567","context":"general"}'
    print(f"\nEjecutando smoke test contra {SANITIZE_URL} ...")
    try:
        r = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "-X", "POST", SANITIZE_URL,
             "-H", "Content-Type: application/json",
             "-H", f"X-Payment: {header}",
             "-d", payload],
            capture_output=True, text=True, timeout=90,
        )
        code = r.stdout.strip()
        print(f"HTTP {code}")
        if code == "200":
            print("✅ Micropago 0.01 USDC en Base VERIFICADO en TrustBoost.")
        else:
            print("⚠️  No 200. Revisa los logs de Render para la linea 'TrustBoost:'.")
    except Exception as e:
        print(f"[ERR] No se pudo ejecutar el curl: {e}")


if __name__ == "__main__":
    main()
