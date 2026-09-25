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

    new = [m for m in msgs if m.get("id") and m.get("id") not in seen]
    if not new:
        print("NO_NEW")
        return

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
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    sys.exit(main())
