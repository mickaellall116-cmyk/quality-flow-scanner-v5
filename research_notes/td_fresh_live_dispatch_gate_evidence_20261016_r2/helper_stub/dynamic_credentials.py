"""Offline trial stub for the platform credential helper surface.

Installed on sys.path ONLY by the r2 holder/contender trial processes.
The dispatch gate must import this module and verify the callable +
allowed-host binding WITHOUT ever invoking it; CALLS must stay empty
through every gate evaluation. (If the gate ever did invoke it, this
stub would attach nothing and return the URL unchanged - it exists to
prove the preflight semantics, not to serve credentials.)
"""
CALLS = []


def url_with_surrogate_query_param(url, credential_ref, allowed_hosts=None):
    CALLS.append({"url": url, "credential_ref": credential_ref,
                  "allowed_hosts": allowed_hosts})
    return url
