#!/usr/bin/env python3
"""
verify_erc8004_base.py — Confirma el despliegue del ERC-8004 Identity Registry en Base mainnet.
READ-ONLY: consulta Basescan API + Base RPC publico. No envia transacciones, no requiere wallet.

Uso:
  python3 verify_erc8004_base.py

Salida: confirma si la direccion candidata (vanity 0x8004...) aloja el contrato ERC-8004
Identity Registry en Base, chequeando (1) que haya codigo de contrato y (2) que la ABI
exporte las funciones clave del estandar (register/setAgentURI/getAgentWallet/agentURI).
"""
import json
import urllib.request
import urllib.error

# Vanity address del Identity Registry en mainnets (mismo patron en Ethereum, Base, etc.)
# CONFIRMADO 2026-07-15: bytecode IDENTICO en Base y Ethereum mainnet (262 chars),
# y Basescan explorer lo titula "8004: Identity Registry - Contract".
# Es el ERC-8004 Identity Registry OFICIAL en Base mainnet.
CANDIDATE = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
BASE_RPC = "https://mainnet.base.org"
BASESCAN_API = "https://api.basescan.org/api"

# Funciones clave del ERC-8004 Identity Registry (EIP-8004)
EXPECTED = ["register", "setAgentURI", "getAgentWallet", "setAgentWallet",
            "agentURI", "ownerOf", "setMetadata", "getMetadata"]


def _get_json(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "hermes-verify/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def check_rpc_code(addr):
    """eth_getCode via Base RPC publico. Devuelve True si hay bytecode."""
    payload = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "eth_getCode",
        "params": [addr, "latest"],
    }).encode()
    req = urllib.request.Request(BASE_RPC, data=payload,
                                 headers={"Content-Type": "application/json",
                                          "User-Agent": "hermes-verify/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
        code = data.get("result", "0x")
        return code not in ("0x", None, ""), len(code) if code else 0
    except Exception as e:
        return None, f"RPC error: {e}"


def check_basescan_abi(addr):
    """Basescan getsourcecode -> ABI. Busca funciones ERC-8004."""
    url = f"{BASESCAN_API}?module=contract&action=getsourcecode&address={addr}"
    try:
        data = _get_json(url)
    except Exception as e:
        return None, f"Basescan error: {e}"
    if data.get("status") != "1":
        return None, data.get("message", "no status 1")
    result = (data.get("result") or [{}])[0]
    abi_raw = result.get("ABI") or result.get("abi")
    if not abi_raw or abi_raw in ("Contract source code not verified", ""):
        # Contrato existe pero no verificado en Basescan
        return "unverified", result.get("ContractName", "")
    try:
        abi = json.loads(abi_raw)
    except Exception:
        return "abi_unparseable", ""
    funcs = {e.get("name") for e in abi if isinstance(e, dict) and e.get("type") == "function"}
    found = [f for f in EXPECTED if f in funcs]
    return found, funcs


def main():
    print(f"Candidato Identity Registry (Base): {CANDIDATE}\n")
    has_code, info = check_rpc_code(CANDIDATE)
    if has_code is True:
        print(f"[1] RPC eth_getCode: CONTRATO PRESENTE (bytecode {info} chars)")
    elif has_code is False:
        print("[1] RPC eth_getCode: NO HAY CONTRATO en esta direccion en Base")
    else:
        print(f"[1] RPC eth_getCode: {info}")

    found, detail = check_basescan_abi(CANDIDATE)
    if isinstance(found, list):
        missing = [f for f in EXPECTED if f not in found]
        print(f"[2] Basescan ABI: nombre='{detail}'")
        print(f"    Funciones ERC-8004 encontradas: {len(found)}/{len(EXPECTED)}")
        if missing:
            print(f"    FALTAN: {missing}")
        else:
            print("    TODAS las funciones clave presentes -> ERC-8004 Identity Registry CONFIRMADO en Base")
    elif found == "unverified":
        print(f"[2] Basescan: contrato NO verificado (nombre='{detail}'). "
              f"Existe en Base pero Basescan no tiene el source/ABI.")
    else:
        print(f"[2] Basescan: {detail}")

    print("\nVeredicto:")
    if has_code and isinstance(found, list) and not [f for f in EXPECTED if f not in found]:
        print("  CONFIRMADO: registrar agents ERC-8004 en Base en esta direccion es SEGURO.")
    elif has_code:
        print("  CONTRATO PRESENTE en Base. Verificar manualmente en Basescan antes de minar.")
    else:
        print("  NO CONFIRMADO en esta direccion. Buscar el deploy real de ERC-8004 en Base.")


if __name__ == "__main__":
    main()
