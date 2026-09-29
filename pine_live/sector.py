"""E1 sector-cap support — SLICE 2.

The frozen SECTOR dict is the SINGLE SOURCE OF TRUTH. It is imported from
pine_exposure.pine_exposure (the research artifact), never copied. The
sha256 of the canonical JSON serialization is pinned at import time: if the
map ever changes, this module refuses to import instead of drifting.

Fail-closed: a symbol without a sector label raises UnknownSectorSymbol.
No default sector, no silent pass-through.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
_EXPOSURE_DIR = os.path.join(_REPO_ROOT, "pine_exposure")
if _EXPOSURE_DIR not in sys.path:
    sys.path.insert(0, _EXPOSURE_DIR)

from pine_exposure import SECTOR  # noqa: E402  (the frozen map, by import)

# Pinned 2026-09-18: sha256 of json.dumps(SECTOR, sort_keys=True).
FROZEN_SECTOR_SHA256 = (
    "9bab23b72dcb18d04935071f2bec94955cb8fa9df96f50dc11b72990dcd7fbb9"
)

SECTOR_SHA256 = hashlib.sha256(
    json.dumps(SECTOR, sort_keys=True).encode("utf-8")
).hexdigest()

if SECTOR_SHA256 != FROZEN_SECTOR_SHA256:
    raise RuntimeError(
        "frozen SECTOR map changed underneath pine_live: "
        f"got {SECTOR_SHA256}, want {FROZEN_SECTOR_SHA256}. "
        "Refusing to import rather than drift."
    )

SECTOR_CAP = 2  # E1: skip a candidate if >=2 positions in its sector are open


class UnknownSectorSymbol(Exception):
    """Raised when a symbol has no frozen sector label. Fail closed."""


def sector_of(symbol: str) -> str:
    """Return the frozen sector for a symbol, or raise (never default)."""
    try:
        return SECTOR[symbol.upper()]
    except KeyError:
        raise UnknownSectorSymbol(
            f"{symbol}: no sector label in the frozen map; "
            "signal generation blocked (fail-closed)"
        )


def sector_counts(positions: dict) -> dict:
    """Count open positions per sector. positions: symbol -> position dict
    with a 'sector' key."""
    counts: dict = {}
    for pos in positions.values():
        s = pos["sector"]
        counts[s] = counts.get(s, 0) + 1
    return counts
