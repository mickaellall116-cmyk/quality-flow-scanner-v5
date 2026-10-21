"""Shadow-observation runner — production binding for the TASK -80 design.

DESIGN-STAGE ONLY. This module is the reviewed specification of how the
shadow observer would be wired to the frozen stack at launch time. It
is NOT installed, NOT scheduled, and NOT executed by the -80 safety
suite (the suite only parses it for the S3 static check). Launching it
requires every item in LAUNCH_READINESS.md, including ChatGPT
adjudication of this package and Mike's explicit launch GO.

WIRING (mirrors the production cycle's data path, minus every part
that writes production state):
    * Universe: the frozen 250 — UX51 from hybrid_exit_test.UNIVERSE_X
      plus the X2 cohort from v54_universe_x2.UNIVERSE_X2, themes
      "Forward-UX51" / "Forward-X2", interval "4h", period "180d" —
      assembled exactly as the production cycle assembles them.
    * Detection: v54_engine.v54_scan_symbols over that universe, then
      v54_engine.v54_qualified_signals. This is the frozen signal path
      itself (same pinned modules, same closed-bar construction), run
      in a separate process that holds no production handles.
    * Bars: v54_engine.m53.download_data(symbol, "4h", "180d") — the
      same Yahoo-backed entry point the production cycle uses —
      converted to plain bar dicts in memory. Per-bar scanner_state
      (the frozen EXIT evaluation input) is computed by classifying
      the symbol on data truncated at each bar, the same information
      rule the production cycle applies.
    * Recording + hypothetical lifecycles: shadow_core.ShadowObserver
      rooted at the shadow namespace directory ONLY.

PIN DISCIPLINE: before any download, verify_pins() hashes every
frozen-stack module this binding depends on and refuses to run on a
mismatch (fail-closed). The production harness module and the
production log module are never imported — they are not dependencies
of observation, and their absence from the import graph is part of
what the S3 check proves.

PROCESS DISCIPLINE (at launch): a separate OS process from the
production harness, invoked with bytecode writing disabled
(python -B) so imports leave no files outside the shadow namespace;
its own scheduler entry; no GitHub publishing in v1.
"""

from __future__ import annotations

import hashlib
import os
import sys
from typing import Any, Dict, List, Tuple

sys.dont_write_bytecode = True

import shadow_core

SHADOW_DIR_NAME = "v54_shadow"
INTERVAL, PERIOD = "4h", "180d"

# Frozen-stack pins, recorded 2026-10-21 from the running stack.
# A mismatch at launch verification = do not observe (fail-closed).
PINNED_STACK = {
    "v54_engine.py": "bde3288307ac7b9bfbded29af89b056ae849f49d91b51c1151dad860224eb8fb",
    "v54_rules.py": "1b55dedce3b17b1670ac7ee75bfcf4375a0162a1daa780a8abb4199c9ebb817a",
    "v54_exit_tracker.py": "3ee92864f1afe98ce543803b8b844c1677a6d0e0ce1a6e61d1b7ea74b329a9e0",
    "scanner_rules.py": "62aa743ac28f05de9b6ec0ab962ee28bb7e5152bbef00bff5afa611a480f473c",
    "masterscanner_api.py": "c3e95b25b114a50c4129360f24f4fd27471b000a7749fe750abf038f1abf0a21",
    "v54_universe_x2.py": "44b0d8ba5a7ea6415652fdfa1e89a0f9bb57d191bfb0d66c578f9d7a3f5880c9",
    "hybrid_exit_test.py": "9140504f6449cafe62e1647ccbacaa384427a56ff111cab8c6e9298a220cf45b",
}


def verify_pins(repo_root: str) -> Dict[str, str]:
    """Hash every pinned stack module; raise on any mismatch."""
    digests: Dict[str, str] = {}
    for name, expected in PINNED_STACK.items():
        path = os.path.join(repo_root, name)
        if not os.path.exists(path):
            raise shadow_core.ShadowError(f"pinned stack module missing: {name}")
        digest = shadow_core.sha256_file(path)
        if digest != expected:
            raise shadow_core.ShadowError(
                f"pin mismatch for {name}: {digest} != {expected}")
        digests[name] = digest
    return digests


def frozen_universe() -> Tuple[List[str], Dict[str, str]]:
    """The frozen 250-symbol universe and theme map (production shape)."""
    import hybrid_exit_test
    import v54_universe_x2 as ux2

    ux51 = list(hybrid_exit_test.UNIVERSE_X)
    x2 = list(ux2.UNIVERSE_X2)
    themes = {s: "Forward-UX51" for s in ux51} | {s: "Forward-X2" for s in x2}
    return ux51 + x2, themes


def detect_candidates(universe: List[str], themes: Dict[str, str],
                      ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[str]]:
    """Run the frozen scan over the full universe.

    Returns (qualified signal rows, regime, scan_degraded_symbols).
    A universe symbol with no usable scan row makes the scan
    incomplete: the core then records a DEGRADED cycle and no signals
    (the Guard 1 analogue — never decide on partial data).
    """
    import v54_engine as eng

    rows, regime = eng.v54_scan_symbols(universe, themes, INTERVAL, PERIOD)
    scanned = {r["symbol"] for r in rows if r.get("state") != "ERROR"}
    scan_degraded = [s for s in universe if s not in scanned]
    return eng.v54_qualified_signals(rows), regime, scan_degraded


def build_frames(symbols: List[str], regime: Dict[str, Any],
                 ) -> Tuple[Dict[str, List[Dict[str, Any]]], List[str]]:
    """Download closed bars per symbol and attach per-bar scanner_state.

    Returns (frames, degraded_symbols). A symbol whose download fails
    or yields no closed bars is degraded: the core will mark the cycle
    DEGRADED and record no new signals from partial data.
    """
    import v54_engine as eng

    frames: Dict[str, List[Dict[str, Any]]] = {}
    degraded: List[str] = []
    market_df = None
    try:
        market_df = eng.m53.download_data(eng.m53.MARKET_SYMBOL, INTERVAL, PERIOD)
    except Exception:
        market_df = None
    for sym in symbols:
        try:
            df = eng.m53.download_data(sym, INTERVAL, PERIOD)
        except Exception:
            degraded.append(sym)
            continue
        if df is None or len(df) == 0:
            degraded.append(sym)
            continue
        bars: List[Dict[str, Any]] = []
        for ts, bar in df.iterrows():
            state = None
            try:
                row = eng.m53.classify_symbol(
                    sym, "Forward-UX51", df[df.index <= ts],
                    market_df[market_df.index <= ts] if market_df is not None else None,
                    regime, INTERVAL)
                state = (row or {}).get("state")
            except Exception:
                state = None
            bars.append({
                "bar_id": ts.isoformat(),
                "open": float(bar["Open"]), "high": float(bar["High"]),
                "low": float(bar["Low"]), "close": float(bar["Close"]),
                "scanner_state": state,
            })
        frames[sym] = bars
    return frames, degraded


def observe_once(repo_root: str) -> Dict[str, Any]:
    """One full observation cycle (the launch-time entry point).

    Order of operations is fail-closed: pins first, then data, then a
    single core cycle. Any pin failure raises before any download.
    """
    verify_pins(repo_root)
    tracker_module = shadow_core.load_pinned_tracker(repo_root)
    observer = shadow_core.ShadowObserver(
        os.path.join(repo_root, SHADOW_DIR_NAME), tracker_module)
    universe, themes = frozen_universe()
    candidates, regime, scan_degraded = detect_candidates(universe, themes)
    live_symbols = {
        lc["symbol"] for lc in observer.state["lifecycles"].values()
        if lc["status"] in ("awaiting_entry", "open")
    }
    needed = sorted({c["symbol"] for c in candidates} | live_symbols)
    frames, frame_degraded = build_frames(needed, regime)
    health = {
        "market_ok": True,
        "scan_complete": not scan_degraded,
        "expected_symbols": needed,
        "degraded_symbols": frame_degraded,
    }
    return observer.run_shadow_cycle(candidates, frames, health)


def main() -> int:
    raise shadow_core.ShadowError(
        "design-stage module: the shadow observer is not launched. "
        "See LAUNCH_READINESS.md — launch requires the completed "
        "checklist, ChatGPT adjudication, and Mike's explicit GO.")


if __name__ == "__main__":
    main()
