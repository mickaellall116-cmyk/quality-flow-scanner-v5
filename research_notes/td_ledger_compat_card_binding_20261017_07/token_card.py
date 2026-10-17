#!/usr/bin/env python3
"""
token_card.py — QF-TD-LEDGER-COMPAT-AND-CARD-BINDING-20261017-07 r1.

Canonical token-request card DERIVED from frozen evidence bytes.

Failure being cured: TOKEN_CARD_WINDOW_DRIFT (-06 r1). The -06 card was
assembled by copying fields; its make_dispatch_token_inputs.window
epochs (1792212067..1792233667) were stale by exactly 1,200 s against
the frozen evidence window (1792213267..1792234867), while its ISO
labels matched the frozen values — a hand-copy error that no check
caught. The card was rejected independently (Issue #1 6230110894).

Contract here: EVERY card field is read from the same canonical frozen
evidence bytes (never independently supplied), ISO labels are computed
from the epochs they label, and verification REGENERATES the card from
the bytes and demands exact equality — any copied/stale/mutated field
HOLDs with the first differing field named.

Note: a derived card proves binding only. The -06 evidence generation
remains NOT token-eligible (gates 3/9 blocked; see the -07 memo). This
module issues nothing.
"""
import hashlib
import json
import time

TASK = "QF-TD-FRESH-LIVE-DISPATCH-GATE-20261016-05"  # pinned wrapper TASK


class CardRefusal(Exception):
    """Frozen bytes cannot yield a card (malformed / missing fields)."""


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def iso(ts):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def make_dispatch_token(run_id, manifest_digest, evidence_digest,
                        ledger_path, window):
    """Byte-identical formula to dispatch_gate_r2.make_dispatch_token."""
    return sha256(canon({
        "dispatch": TASK, "run_id": run_id,
        "manifest_digest": manifest_digest,
        "evidence_digest": evidence_digest, "ledger_path": ledger_path,
        "window_start": window["start"], "window_end": window["end"],
    }))


def _require(cond, msg):
    if not cond:
        raise CardRefusal(msg)


def derive_inputs(frozen_bytes):
    """Read every token input from the frozen evidence bytes themselves."""
    try:
        ev = json.loads(frozen_bytes)
    except ValueError:
        raise CardRefusal("FROZEN_MALFORMED_JSON")
    _require(isinstance(ev, dict), "FROZEN_NOT_OBJECT")
    pk = ev.get("packet")
    _require(isinstance(pk, dict), "FROZEN_PACKET_MISSING")
    win = pk.get("dispatch_window")
    _require(isinstance(win, dict), "FROZEN_WINDOW_MISSING")
    start, end = win.get("start"), win.get("end")
    _require(isinstance(start, int) and not isinstance(start, bool)
             and isinstance(end, int) and not isinstance(end, bool),
             "FROZEN_WINDOW_NOT_INT_EPOCH")
    _require(end > start, "FROZEN_WINDOW_INVERTED")
    for k in ("run_id", "manifest_digest", "ledger_path"):
        _require(isinstance(pk.get(k), str) and pk[k],
                 "FROZEN_FIELD_MISSING:%s" % k)
    return {
        "run_id": pk["run_id"],
        "manifest_digest": pk["manifest_digest"],
        "evidence_digest": sha256(frozen_bytes),
        "ledger_path": pk["ledger_path"],
        "window": {"start": start, "end": end},
    }


def derive_card(frozen_bytes):
    """Build the canonical card from frozen bytes. Deterministic."""
    inputs = derive_inputs(frozen_bytes)
    card = {
        "card": "TOKEN_REQUEST_DERIVED",
        "task": "QF-TD-LEDGER-COMPAT-AND-CARD-BINDING-20261017-07",
        "status": ("HOLD - binding proof only; NOT token-eligible while "
                   "gates 3/9 remain blocked (see -07 memo)"),
        "make_dispatch_token_inputs": inputs,
        "window_iso": {"start": iso(inputs["window"]["start"]),
                       "end": iso(inputs["window"]["end"])},
        "token_preview": make_dispatch_token(
            inputs["run_id"], inputs["manifest_digest"],
            inputs["evidence_digest"], inputs["ledger_path"],
            inputs["window"]),
    }
    card["card_digest"] = sha256(canon(card))
    return card


def _first_diff(a, b, path=""):
    if type(a) is not type(b):
        return path or "<root>"
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                return "%s.%s" % (path, k) if path else k
            d = _first_diff(a[k], b[k], "%s.%s" % (path, k) if path else k)
            if d is not None:
                return d
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return path
        for i, (x, y) in enumerate(zip(a, b)):
            d = _first_diff(x, y, "%s[%d]" % (path, i))
            if d is not None:
                return d
        return None
    return None if a == b else path


def verify_card(frozen_bytes, presented_card):
    """Return (True, 'BOUND') iff presented_card is EXACTLY the card
    derived from frozen_bytes; else (False, 'HOLD:<first differing
    field>'). Any copied or stale field fails."""
    try:
        derived = derive_card(frozen_bytes)
    except CardRefusal as e:
        return False, "HOLD:FROZEN_UNUSABLE:%s" % e
    if not isinstance(presented_card, dict):
        return False, "HOLD:CARD_NOT_OBJECT"
    diff = _first_diff(derived, presented_card)
    if diff is None:
        return True, "BOUND"
    return False, "HOLD:FIELD_MISMATCH:%s" % diff
