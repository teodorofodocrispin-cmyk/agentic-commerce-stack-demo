#!/usr/bin/env python3
"""
proofmesh_search.py — Busca posts relevantes en Moltbook por keyword, rankeado por engagement.

PATRON CRITICO (Ivar 2026-07-14): la terminal del usuario NO inyecta la key con
`$(cat ~/.moltbook_key)` ni `-K` (envia `***` literal -> 401). La UNICA tecnica que
funciona es leer la key del archivo con open() y usar urllib con header Bearer {K}.

Uso:
  python3 proofmesh_search.py                # usa DEFAULT_KW
  python3 proofmesh_search.py eu ai act x402 # keywords propios

El script escanea /feed y /submolts/general/feed, filtra por keyword y ordena por
comment_count (engagement). NO publica nada — solo lista objetivos.
"""
import json
import urllib.request
import os
import sys

KEY = open(os.path.expanduser('~/.moltbook_key')).read().strip()
BASE = 'https://www.moltbook.com/api/v1'

DEFAULT_KW = [
    'eu ai act', 'ai act', 'x402', 'pii', 'latam', 'market entry', 'compliance',
    'sanctions', 'kyb', 'kyc', 'stablecoin', 'agent payment', 'data governance',
    'provenance', 'gdpr', 'regulation', 'verified data', 'screening',
]


def _get(path):
    req = urllib.request.Request(
        f'{BASE}{path}',
        headers={'Authorization': f'Bearer {KEY}'},
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def fetch_posts():
    out = {}
    paths = ['/feed?limit=500', '/submolts/general/feed?limit=500']
    # Submolts ampliados para encontrar threads FRESCOS (no los quemados por spam)
    for sub in ['ai', 'ai-policy', 'compliance', 'latam', 'stablecoin', 'payments',
                'agents', 'policy', 'regulation', 'privacy', 'data']:
        paths.append(f'/submolts/{sub}/feed?limit=200')
    for path in paths:
        try:
            d = _get(path)
            for p in (d.get('posts') or []):
                out[p['id']] = p
        except Exception as e:
            print(f'  (warn) {path} -> {e}', file=sys.stderr)
    return list(out.values())


def main():
    kws = [k.lower() for k in sys.argv[1:]] or DEFAULT_KW
    posts = fetch_posts()
    hits = []
    for p in posts:
        text = ((p.get('title') or '') + ' ' + (p.get('content') or '')).lower()
        matched = [k for k in kws if k in text]
        if matched:
            hits.append((
                p.get('comment_count') or 0,
                p.get('id'),
                (p.get('author') or {}).get('name'),
                (p.get('title') or '')[:70],
                matched,
            ))
    hits.sort(reverse=True)
    print(f'=== {len(hits)} posts relevantes (ranked by engagement) ===')
    if not hits:
        print('Sin hits en el feed actual. Proba keywords distintas o mas submolts.')
        return
    for c, pid, author, title, matched in hits:
        print(f'[{c:>4}] @{author:18} {pid}')
        print(f'       {title}')
        print(f'       kw: {", ".join(matched)}')


if __name__ == '__main__':
    main()
