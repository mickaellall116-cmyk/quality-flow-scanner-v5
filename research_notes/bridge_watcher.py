#!/usr/bin/env python3
"""Quality Flow research bridge watcher.

Polls the Muse Gmail mailbox for new messages on the standing research
bridge thread (subject: QUALITY FLOW — AGENT RESEARCH BRIDGE) and reports
only messages not seen before. State lives in bridge_state.json next to
this script. Prints either NO_NEW or a JSON list of new messages.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(HERE, "bridge_state.json")
SUBJECT = "QUALITY FLOW — AGENT RESEARCH BRIDGE"


def gws(*args):
    r = subprocess.run(
        ["hatch_gws_cli", "gmail"] + list(args),
        capture_output=True, text=True, timeout=60,
    )
    return r.stdout.strip()


def gh_api(path):
    """GET against api.github.com using the custom.github connector."""
    import urllib.request
    sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
    from dynamic_credentials import add_surrogate_to_request, read_json_response
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        method="GET",
        headers={"Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "User-Agent": "research-bridge-watcher"},
    )
    add_surrogate_to_request(req, "custom.github", allowed_hosts=["api.github.com"])
    with urllib.request.urlopen(req, timeout=60) as resp:
        return read_json_response(resp)


def load_state():
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"seen_ids": []}


def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f)


def main():
    state = load_state()
    seen = set(state.get("seen_ids", []))

    raw = gws("+triage", "--max", "30",
              "--query", '{from:quality-flow-research@agentmail.to subject:"AGENT RESEARCH BRIDGE"} newer_than:3d',
              "--format", "json")
    try:
        data = json.loads(raw) if raw else []
    except json.JSONDecodeError:
        print("NO_NEW")
        return
    msgs = data.get("messages", []) if isinstance(data, dict) else data
    if not isinstance(msgs, list):
        print("NO_NEW")
        return

    new = []
    for m in msgs:
        mid = m.get("id")
        frm = (m.get("from") or m.get("sender") or "").lower()
        if not mid or mid in seen:
            continue
        # Skip our own outbound sends: the bridge mailbox holds copies of
        # messages Muse sends from its own Gmail; only ChatGPT's replies
        # (via AgentMail) count as new bridge traffic.
        if "mickaellall116@gmail.com" in frm:
            seen.add(mid)
            continue
        new.append(m)
    out = []
    for m in new:
        mid = m["id"]
        body = gws("+read", "--id", mid, "--format", "json")
        try:
            detail = json.loads(body) if body else {}
        except json.JSONDecodeError:
            detail = {"raw": body[:500]}
        out.append({
            "id": mid,
            "from": m.get("from") or m.get("sender"),
            "subject": m.get("subject"),
            "date": m.get("date"),
            "snippet": (detail.get("body_text") or detail.get("body") or detail.get("snippet") or "")[:4000],
        })
        seen.add(mid)

    state["seen_ids"] = sorted(seen)[-200:]
    save_state(state)

    # GitHub bridge: poll issue #1 comments (ChatGPT's reply surface).
    # Muse posts via research_notes/bridge_thread.md commits because its
    # token cannot post issue comments.
    gh_seen = set(state.get("seen_gh_comments", []))
    try:
        comments = gh_api("/repos/mickaellall116-cmyk/quality-flow-scanner-v5"
                          "/issues/1/comments?per_page=30")
    except Exception:
        comments = []
    for c in comments:
        cid = str(c.get("id"))
        if not cid or cid in gh_seen:
            continue
        # Do NOT skip by author. ChatGPT's bridge posts arrive under
        # mickaellall116-cmyk (the same account Mike uses), so an author
        # skip silently drops ChatGPT's replies. Surface every new comment
        # with its author; the consumer decides by content (ChatGPT's
        # bridge messages carry TYPE: markers).
        author = (c.get("user") or {}).get("login", "")
        out.append({
            "id": f"gh-{cid}",
            "from": author,
            "subject": "Quality Flow Research Bridge (issue #1)",
            "date": c.get("created_at"),
            "snippet": (c.get("body") or "")[:4000],
        })
        gh_seen.add(cid)
    state["seen_gh_comments"] = sorted(gh_seen)[-200:]
    save_state(state)

    if not out:
        print("NO_NEW")
        return
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    sys.exit(main())
