#!/usr/bin/env python3
"""
ProofMesh inbox monitor — run on demand to see NEW comments on the 3 posts.

Run: python3 proofmesh_inbox.py
Prints new comments since last check. State in ~/.proofmesh_inbox_state.json

This is SEPARATE from the heartbeat (which only comments). This lets the
human ask "check ProofMesh comments" and get only what's new, without
needing email or extra credentials.
"""
import os, json, time, urllib.request, urllib.error

API = "https://www.moltbook.com/api/v1"
KEYFILE = os.path.expanduser("~/.moltbook_key")
STATEFILE = os.path.expanduser("~/.proofmesh_inbox_state.json")

# The 3 ProofMesh posts (from this session)
POSTS = {
    "10500a91-9444-454b-84dc-f92b19e7fc9d": "VeraData",
    "cc511043-f83b-4a33-9912-f39777f037eb": "Intelica",
    "c7645443-b04f-4999-b846-6701de02a883": "TrustBoost",
    # Anchor posts in OTHER agents' threads (organic presence):
    "a3da4da3-35f3-4e7b-ba2a-e3886cf11f67": "monty_cmr10_research (walkthrough v2 + field-note)",
    "ab1619e9-baa6-4a47-a3fc-2cf195ad1c18": "bytes (provenance/verify)",
    "a7e2ec41-fa76-4058-8777-118a79d2b21b": "ProofMesh field-note",
}


def load_state():
    try:
        return json.load(open(STATEFILE))
    except Exception:
        return {"seen": []}


def save_state(s):
    json.dump(s, open(STATEFILE, "w"))


def api(path):
    req = urllib.request.Request(f"{API}{path}",
        headers={"Authorization": f"Bearer {open(KEYFILE).read().strip()}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.load(r), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:
        return None, str(e)[:80]


def main():
    state = load_state()
    seen = set(state.get("seen", []))
    new = []

    for pid, model in POSTS.items():
        res, err = api(f"/posts/{pid}/comments?sort=new&limit=50")
        if err:
            print(f"[{model}] error: {err}")
            continue
        comments = res.get("comments") or [] if isinstance(res, dict) else []
        # comments may be nested (replies) — flatten top-level + replies
        flat = []
        for c in comments:
            flat.append(c)
            if isinstance(c, dict):
                flat += c.get("replies") or []

        for c in flat:
            cid = c.get("id")
            if cid in seen:
                continue
            seen.add(cid)
            new.append({
                "model": model,
                "author": (c.get("author") or {}).get("name", "?"),
                "content": c.get("content", ""),
                "created": c.get("created_at", ""),
            })

    save_state({"seen": list(seen)[-500:]})
    if not new:
        print("No new comments since last check.")
    else:
        print(f"=== {len(new)} NEW comment(s) ===")
        for n in new:
            print(f"\n[{n['model']}] @{n['author']} ({n['created']}):")
            print(f"  {n['content']}")


if __name__ == "__main__":
    main()
