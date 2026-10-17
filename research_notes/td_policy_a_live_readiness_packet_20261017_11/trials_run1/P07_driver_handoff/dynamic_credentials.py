"""Offline trial stub for the platform credential helper surface.

Installed at the exact test seam ONLY (the -08 gate resolves it by
exact path + pinned hash via credential_resolver; it is never found
through sys.path). The gate/resolver must verify the callable +
allowed-host binding WITHOUT ever invoking it; every invocation is
appended to calls.jsonl beside this file so any loader instance is
observable. (If it ever were invoked, it would attach nothing and
return the URL unchanged - it exists to prove the verification and
handoff semantics, not to serve credentials.)
"""
import json
import os

CALLS = []


def url_with_surrogate_query_param(url, credential_ref, allowed_hosts=None):
    CALLS.append({"url": url, "credential_ref": credential_ref,
                  "allowed_hosts": allowed_hosts})
    try:
        log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calls.jsonl")
        with open(log, "a") as f:
            f.write(json.dumps({"invoked": True}) + "\n")
    except Exception:
        pass
    return url
# tamper
