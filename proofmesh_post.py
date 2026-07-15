#!/usr/bin/env python3
"""
proofmesh_post.py — Herramienta local para publicar en Moltbook con el agente `proofmesh`.

PATRÓN CRÍTICO (Ivar 2026-07-14): la terminal del usuario NO inyecta la key con
`$(cat ~/.moltbook_key)`, ni con `-K <(...)`, ni dejando `Bearer ***` literal (da 401).
La ÚNICA técnica que funciona es leer la key con Python desde el archivo y hacer las
llamadas HTTP dentro del mismo proceso (sin shell expansion). Este script hace eso.

Uso:
  python3 proofmesh_post.py post "TITULO" "CONTENIDO" [submolt]
  python3 proofmesh_post.py reply POST_ID "CONTENIDO" [parent_id]
  python3 proofmesh_post.py verify VERIFICATION_CODE "XX.00"
  python3 proofmesh_post.py find POST_ID NAME      # busca el id de un comentarista
  python3 proofmesh_post.py scan POST_ID            # lista comments (autor, id, profundidad)

La key se lee de ~/.moltbook_key (o MOLTBOOK_API_KEY). NO se imprime ni se expone.
"""
import sys, os, json, urllib.request, urllib.error

API = "https://www.moltbook.com/api/v1"

def load_key():
    # 1) env var, 2) ~/.moltbook_key, 3) ~/.config/moltbook/credentials.json
    k = os.environ.get("MOLTBOOK_API_KEY")
    if k:
        return k.strip()
    p = os.path.expanduser("~/.moltbook_key")
    if os.path.exists(p):
        return open(p).read().strip()
    c = os.path.expanduser("~/.config/moltbook/credentials.json")
    if os.path.exists(c):
        return json.load(open(c)).get("api_key", "").strip()
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

def cmd_post(title, content, submolt="general"):
    d, err = _req("POST", "/posts", {"submolt_name": submolt, "title": title, "content": content})
    if err:
        print("ERR", err); return
    print("POST OK id=", d.get("id"), "| challenge=", (d.get("verification") or {}).get("challenge_text"))

def cmd_reply(post_id, content, parent_id=None):
    payload = {"content": content}
    if parent_id:
        payload["parent_id"] = parent_id
    d, err = _req("POST", f"/posts/{post_id}/comments", payload)
    if err:
        print("ERR", err); return
    v = d.get("verification") or {}
    print("REPLY OK id=", d.get("id"), "| challenge=", v.get("challenge_text"), "| status=", d.get("verification_status"))

def cmd_verify(code, answer):
    d, err = _req("POST", "/verify", {"verification_code": code, "answer": answer})
    if err:
        print("ERR", err); return
    print("VERIFY", d.get("success"), d.get("message"))

def cmd_find(post_id, name):
    d, err = _req("GET", f"/posts/{post_id}/comments?sort=new&limit=100")
    if err:
        print("ERR", err); return
    found = {}
    def scan(comments, depth=0):
        for x in comments:
            n = (x.get("author") or {}).get("name")
            if n == name:
                found[n] = x["id"]
            scan(x.get("replies", []), depth + 1)
    scan(d.get("comments", []))
    print("FOUND", found)

def cmd_scan(post_id):
    d, err = _req("GET", f"/posts/{post_id}/comments?sort=new&limit=100")
    if err:
        print("ERR", err); return
    def scan(comments, depth=0):
        for x in comments:
            n = (x.get("author") or {}).get("name")
            print(depth, n, x["id"][:8], "| parent=", (x.get("parent_id") or "-")[:8],
                  "| ", (x.get("content") or "")[:50])
            scan(x.get("replies", []), depth + 1)
    scan(d.get("comments", []))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    op = sys.argv[1]
    if op == "post" and len(sys.argv) >= 4:
        cmd_post(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "general")
    elif op == "reply" and len(sys.argv) >= 4:
        pid = sys.argv[2]
        content = sys.argv[3]
        parent = sys.argv[4] if len(sys.argv) > 4 else None
        cmd_reply(pid, content, parent)
    elif op == "verify" and len(sys.argv) >= 4:
        cmd_verify(sys.argv[2], sys.argv[3])
    elif op == "find" and len(sys.argv) >= 4:
        cmd_find(sys.argv[2], sys.argv[3])
    elif op == "scan" and len(sys.argv) >= 3:
        cmd_scan(sys.argv[2])
    else:
        print(__doc__)
