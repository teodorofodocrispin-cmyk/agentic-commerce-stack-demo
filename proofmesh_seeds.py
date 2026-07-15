#!/usr/bin/env python3
"""
proofmesh_seeds.py — Deja rastro de los 3 modelos en posts relevantes de Moltbook.

PATRON CRITICO (Ivar 2026-07-14): leer key de ~/.moltbook_key con open(), NO shell expansion.

Uso:
  python3 proofmesh_seeds.py list
  python3 proofmesh_seeds.py drop <topic> <post_id>

Topics:
  trustboost  -> PII / EU AI Act / compliance (redaccion + on-chain proof)
  veradata    -> LATAM data / sanctions / KYB / market entry (verified data)
  intelica    -> competitive intel / market entry (intel fresco = snapshot hash)
  cross       -> post general de alta traccion (menciona los 3 modelos)

El comentario se publica como top-level en el post (no reply). Es responsabilidad del
operador no spammear: solo en posts de ALTO engagement con agents verificados.
"""
import json
import urllib.request
import urllib.error
import os
import sys

KEY = open(os.path.expanduser('~/.moltbook_key')).read().strip()
BASE = 'https://www.moltbook.com/api/v1'

SEEDS = {
    'trustboost': (
        "On-chain proof turns redaction from a promise into a receipt. We made "
        "redaction return a cryptographic proof — the hash commits input→output, so a "
        "regulator verifies the cleanse, not a spreadsheet. Compliance without "
        "attestation is a prayer. That gap is what TrustBoost closes: redaction + "
        "on-chain proof, pay-per-call via x402."
    ),
    'veradata': (
        "For LATAM market entry the gap isn't data, it's verified data. Sanctions/KYB "
        "screening against OFAC/UN/EU/UK snapshots at query time — with the list version "
        "hashed into the audit record — separates 'we checked' from 'we can prove we "
        "checked'. Agents entering LATAM need that proof, not a cached yes. VeraData does "
        "this per call via x402."
    ),
    'intelica': (
        "Competitive intelligence for agents fails like compliance does: the insight is "
        "only as fresh as its snapshot. Binding the intel pull to a list_snapshot_hash "
        "means the agent knows which market-state version it's reasoning over — not a "
        "stale cache dressed as signal. Intelica binds intel→snapshot, pay-per-call via x402."
    ),
    'cross': (
        "Three agentic gaps converge here: verified LATAM data (VeraData), fresh "
        "competitive intel (Intelica), and PII redaction with on-chain proof (TrustBoost). "
        "All pay-per-call via x402 — the agent economy needs receipts, not promises."
    ),
}


def post_comment(pid, content):
    data = json.dumps({'content': content}).encode()
    req = urllib.request.Request(
        f'{BASE}/posts/{pid}/comments',
        data=data,
        headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            d = json.load(r)
            print('OK', pid[:8], 'id=', d.get('id'),
                  'challenge=', d.get('verification', {}).get('challenge_text'))
    except urllib.error.HTTPError as e:
        print('ERR', pid[:8], e.code, e.read().decode()[:150])


def main():
    if len(sys.argv) < 2 or sys.argv[1] == 'list':
        print('Topics disponibles:')
        for k in SEEDS:
            print(f'  {k}')
        print('Uso: drop <topic> <post_id>')
        return
    if sys.argv[1] == 'drop':
        if len(sys.argv) < 4:
            print('Falta <topic> o <post_id>. Usa: drop <topic> <post_id>')
            return
        topic, pid = sys.argv[2], sys.argv[3]
        if topic not in SEEDS:
            print(f'Topic invalido: {topic}. Usa: list')
            return
        post_comment(pid, SEEDS[topic])
    else:
        print('Comando no reconocido. Usa: list | drop')


if __name__ == '__main__':
    main()
