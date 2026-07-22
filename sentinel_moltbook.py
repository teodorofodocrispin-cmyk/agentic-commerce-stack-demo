#!/usr/bin/env python3
"""
sentinel_moltbook.py — Herramienta local para SENTINEL en Moltbook.

PATRON CRITICO (Ivar 2026-07-14, probado con proofmesh): la terminal del usuario NO
inyecta la key con `$(cat ~/.moltbook_key)`, ni con `-K <(...)`, ni dejando
`Bearer ***` literal (da 401). La UNICA tecnica que funciona es leer la key con
Python desde el archivo y hacer las llamadas HTTP dentro del mismo proceso.

Uso:
  python3 sentinel_moltbook.py search [keywords...]   # lista posts por engagement
  python3 sentinel_moltbook.py post "TITULO" "CONTENIDO" [submolt]
  python3 sentinel_moltbook.py reply POST_ID "CONTENIDO" [parent_id]
  python3 sentinel_moltbook.py submolt "NOMBRE" "DESCRIPCION"   # crea submolt propio
  python3 sentinel_moltbook.py scan POST_ID             # lista comments

La key se lee de ~/.moltbook_key (o MOLTBOOK_API_KEY). NO se imprime ni se expone.
"""
import sys, os, json, urllib.request, urllib.error

API = "https://www.moltbook.com/api/v1"

DEFAULT_KW = [
    'x402', 'agent payment', 'agentic payment', 'payment protocol', 'autonomous agent',
    'agent security', 'agent safety', 'safety oracle', 'transaction safety', 'ai agent',
    'mtp', 'a2a', 'ap2', 'ucp', 'agent commerce', 'micropayment', 'usdc', 'base',
    'honeypot', 'rug', 'malicious', 'pre-execution', 'onchain', 'web3 agent',
]


def load_key():
    k = os.environ.get("MOLTBOOK_API_KEY")
    if k:
        return k.strip()
    p = os.path.expanduser("~/.moltbook_key")
    if os.path.exists(p):
        return open(p).read().strip()
    raise SystemExit("No Moltbook key found. Set MOLTBOOK_API_KEY or ~/.moltbook_key")


KEY = load_key()


def _req(method, path, data=None):
    headers = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(API + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.load(r), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read().decode()[:160]}"


def fetch_posts():
    out = {}
    paths = ['/feed?limit=500', '/submolts/general/feed?limit=500']
    for sub in ['ai', 'ai-policy', 'agents', 'payments', 'agentic-commerce',
                'crypto', 'web3', 'security', 'dev', 'policy', 'base', 'stablecoin',
                'autonomous', 'x402', 'agent-payments']:
        paths.append(f'/submolts/{sub}/feed?limit=200')
    for path in paths:
        try:
            d = _req("GET", path)[0]
            if d is None:
                continue
            for p in (d.get('posts') or []):
                out[p['id']] = p
        except Exception as e:
            print(f'  (warn) {path} -> {e}', file=sys.stderr)
    return list(out.values())


def cmd_search():
    kws = [k.lower() for k in sys.argv[2:]] or DEFAULT_KW
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
                (p.get('submolt') or {}).get('name') if isinstance(p.get('submolt'), dict) else p.get('submolt'),
            ))
    hits.sort(reverse=True)
    print(f'=== {len(hits)} posts relevantes para SENTINEL (ranked by engagement) ===')
    if not hits:
        print('Sin hits. Proba keywords distintas o mas submolts.')
        return
    for c, pid, author, title, matched, sub in hits:
        print(f'[{c:>4}] @{author}  submolt={sub}')
        print(f'       id={pid}')
        print(f'       {title}')
        print(f'       kw: {", ".join(matched)}')
        print()


def cmd_post():
    if len(sys.argv) < 4:
        print("Uso: post TITULO CONTENIDO [submolt]"); return
    title, content = sys.argv[2], sys.argv[3]
    submolt = sys.argv[4] if len(sys.argv) > 4 else "general"
    d, err = _req("POST", "/posts", {"submolt_name": submolt, "title": title, "content": content})
    if err:
        print("ERR", err); return
    print("POST OK id=", d.get("id"), "| challenge=", (d.get("verification") or {}).get("challenge_text"))


def cmd_postfile():
    """Lee titulo y contenido de archivos (evita problemas de shell quoting)."""
    if len(sys.argv) < 4:
        print("Uso: postfile ARCHIVO_TITULO ARCHIVO_CONTENIDO [submolt]"); return
    title = open(os.path.expanduser(sys.argv[2])).read().strip()
    content = open(os.path.expanduser(sys.argv[3])).read().strip()
    submolt = sys.argv[4] if len(sys.argv) > 4 else "general"
    d, err = _req("POST", "/posts", {"submolt_name": submolt, "title": title, "content": content})
    if err:
        print("ERR", err); return
    print("POST OK id=", d.get("id"), "| challenge=", (d.get("verification") or {}).get("challenge_text"))


def cmd_reply():
    if len(sys.argv) < 4:
        print("Uso: reply POST_ID CONTENIDO [parent_id]"); return
    pid, content = sys.argv[2], sys.argv[3]
    parent = sys.argv[4] if len(sys.argv) > 4 else None
    payload = {"content": content}
    if parent:
        payload["parent_id"] = parent
    d, err = _req("POST", f"/posts/{pid}/comments", payload)
    if err:
        print("ERR", err); return
    v = d.get("verification") or {}
    print("REPLY OK id=", d.get("id"), "| challenge=", v.get("challenge_text"), "| status=", d.get("verification_status"))


def cmd_replyfile():
    """Lee el contenido de un archivo (evita problemas de shell quoting con comillas/em-dash)."""
    if len(sys.argv) < 4:
        print("Uso: replyfile POST_ID ARCHIVO_CONTENIDO [parent_id]"); return
    pid, fpath = sys.argv[2], sys.argv[3]
    parent = sys.argv[4] if len(sys.argv) > 4 else None
    content = open(os.path.expanduser(fpath)).read().strip()
    payload = {"content": content}
    if parent:
        payload["parent_id"] = parent
    d, err = _req("POST", f"/posts/{pid}/comments", payload)
    if err:
        print("ERR", err); return
    v = d.get("verification") or {}
    print("REPLY OK id=", d.get("id"), "| challenge=", v.get("challenge_text"), "| status=", d.get("verification_status"))


def cmd_submolt():
    if len(sys.argv) < 4:
        print("Uso: submolt NOMBRE DESCRIPCION"); return
    name, desc = sys.argv[2], sys.argv[3]
    # Moltbook requiere display_name (string visible) ademas de name (slug)
    d, err = _req("POST", "/submolts", {
        "name": name,
        "display_name": name.upper(),
        "description": desc,
    })
    if err:
        print("ERR", err); return
    print("SUBMOLT OK", d)


def cmd_scan():
    if len(sys.argv) < 3:
        print("Uso: scan POST_ID"); return
    d, err = _req("GET", f"/posts/{sys.argv[2]}/comments?sort=new&limit=100")
    if err:
        print("ERR", err); return
    def scan(comments, depth=0):
        for x in comments:
            n = (x.get("author") or {}).get("name")
            print(depth, n, x["id"][:8], "| parent=", (x.get("parent_id") or "-")[:8],
                  "| ", (x.get("content") or "")[:50])
            scan(x.get("replies", []), depth + 1)
    scan(d.get("comments", []))


def cmd_inspect():
    """Muestra metadata del post (incluida la fecha) antes de comentar."""
    if len(sys.argv) < 3:
        print("Uso: inspect POST_ID"); return
    pid = sys.argv[2]
    d, err = _req("GET", f"/posts/{pid}")
    if err:
        print("ERR", err); return
    # Moltbook anida el post bajo la clave "post"
    post = d.get("post", d) if isinstance(d, dict) else {}
    for f in ("created_at", "published_at", "timestamp", "createdAt", "date", "updated_at"):
        if f in post:
            print(f"{f}:", post[f])
    print("author:", (post.get("author") or {}).get("name"))
    print("comment_count:", post.get("comment_count"))
    print("title:", (post.get("title") or "")[:80])
    known = ("created_at", "published_at", "timestamp", "createdAt", "date", "updated_at")
    if not any(f in post for f in known):
        print("--- JSON completo (busca el campo de fecha) ---")
        print(json.dumps(post, indent=2)[:1200])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(0)
    op = sys.argv[1]
    if op == "search":
        cmd_search()
    elif op == "post":
        cmd_post()
    elif op == "postfile":
        cmd_postfile()
    elif op == "reply":
        cmd_reply()
    elif op == "replyfile":
        cmd_replyfile()
    elif op == "submolt":
        cmd_submolt()
    elif op == "scan":
        cmd_scan()
    elif op == "inspect":
        cmd_inspect()
    else:
        print(__doc__)
