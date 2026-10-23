"""Shadow signal-only runner — production binding for the -80 successor.

OPERATIONAL ENTRYPOINT (closes -80 blocker B1): main() is real.
It has exactly two modes:

  * --dry-run --fixture <file.json>: runs one full cycle against a
    synthetic fixture adapter. No network, no production imports
    are executed, all writes go to --root. This is the mode the
    acceptance suite exercises end-to-end, and the mode a
    supervised first-cycle rehearsal uses.
  * live (no --dry-run): REFUSES unless the shadow root contains a
    LAUNCH_AUTHORIZED.json artifact naming the same T0 — that
    artifact is created only by Mike's explicit launch GO, which
    has NOT been given for this candidate. The refusal happens
    before any download or adapter use.

WIRING (live mode, mirrors -80's binding minus every lifecycle
part): the frozen 250-name cohort (UX51 from
hybrid_exit_test.UNIVERSE_X + X2 from v54_universe_x2.UNIVERSE_X2),
detection by the frozen v54_engine scan path over closed 4H bars,
recording by shadow_signal_core.SignalObserver rooted at the
shadow namespace ONLY.

HEALTH HONESTY (closes B2): market_ok is DERIVED from an actual
market-frame fetch in the same cycle (download_data on the market
symbol): exception, None, or empty => market_ok False => the core
records a DEGRADED cycle and no signals. scan_complete is derived
from actual scan-row coverage of the cohort.

PIN DISCIPLINE: verify_pins() hashes every frozen-stack module
the live adapter depends on BEFORE any adapter use and refuses on
mismatch (fail-closed). The production harness and log writer are
never imported. The Mode B exit tracker is deliberately NOT a
dependency at this stage (nothing is simulated), so it is neither
pinned nor loaded — a disclosed divergence from -80, whose core
loaded it for hypothetical lifecycles this stage does not run.

WORKLOAD BOUND: one cycle = one scan pass over the cohort + one
market-frame fetch, the same data cost as one ordinary production
scan cycle; no retries, no extra symbols, no publishing.

REPAIR 2026-10-22 (V5, shadow_successor_repair_20261022 —
candidate copy; the 798de18 successor is untouched): the parity
verification (d5a4fe6, check V5) spy-proved that LiveAdapter
.fetch() computed market_ok=False on market-frame failure and
then called v54_scan_symbols over the FULL 250-name cohort
anyway (spy: 1 scan call / 250 symbols, both raise and None
modes; required 0). The 24/24 acceptance suite missed it
because its fetch-count test exercises the FixtureAdapter path
only. HERE: fetch() returns BEFORE any cohort scan when the
market frame is not positively OK (exception, None, or empty),
reporting market_ok False and scan_complete False — the core
records the cycle DEGRADED and nothing is scanned, so a blind
cycle costs exactly one market fetch. The regression test
(test_v5v8_repair.py) drives THIS LiveAdapter with the same
stub-spy method the verification used. Also added: --verify-log
runs the core's external hash-chain anchor verification against
an existing shadow root, read-only.

CLOSEOUT 2026-10-22 (shadow_closeout_20261022 — candidate copy;
the LiveAdapter wiring is byte-identical to the repair's: the
closeout assignment forbids LiveAdapter changes beyond what
the fixtures need, and none were needed): observe_once now
additionally verifies the adapter-reported expected universe
against the core's pinned ordered-universe digest before the
cycle runs (a reordered or altered cohort refuses), passes an
optional external anchor path through to the core, and
--verify-log accepts --anchor <file>: a missing anchor file
or an anchor mismatch exits 2, fail-closed. Live mode still
refuses without LAUNCH_AUTHORIZED.json; this package creates
no authorization artifact, no shadow root, and no scheduler.
Launch remains HOLD.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

sys.dont_write_bytecode = True

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shadow_signal_core as core  # noqa: E402

SHADOW_DIR_NAME = "v54_shadow"
INTERVAL, PERIOD = "4h", "180d"
AUTH_FILENAME = "LAUNCH_AUTHORIZED.json"

# Frozen-stack pins for the modules the LIVE adapter depends on.
# Re-verified 2026-10-22 against the running stack: all six match
# the -80 package's recorded pins byte-for-byte.
PINNED_STACK = {
    "v54_engine.py": "bde3288307ac7b9bfbded29af89b056ae849f49d91b51c1151dad860224eb8fb",
    "v54_rules.py": "1b55dedce3b17b1670ac7ee75bfcf4375a0162a1daa780a8abb4199c9ebb817a",
    "scanner_rules.py": "62aa743ac28f05de9b6ec0ab962ee28bb7e5152bbef00bff5afa611a480f473c",
    "masterscanner_api.py": "c3e95b25b114a50c4129360f24f4fd27471b000a7749fe750abf038f1abf0a21",
    "v54_universe_x2.py": "44b0d8ba5a7ea6415652fdfa1e89a0f9bb57d191bfb0d66c578f9d7a3f5880c9",
    "hybrid_exit_test.py": "9140504f6449cafe62e1647ccbacaa384427a56ff111cab8c6e9298a220cf45b",
}


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_pins(repo_root: str) -> Dict[str, str]:
    """Hash every pinned stack module; raise on any mismatch."""
    digests: Dict[str, str] = {}
    for name, expected in PINNED_STACK.items():
        path = os.path.join(repo_root, name)
        if not os.path.exists(path):
            raise core.ShadowError(f"pinned stack module missing: {name}")
        digest = _sha256_file(path)
        if digest != expected:
            raise core.ShadowError(
                f"pin mismatch for {name}: {digest} != {expected}")
        digests[name] = digest
    return digests


def frozen_universe() -> Tuple[List[str], Dict[str, str]]:
    """The frozen 250-symbol universe and theme map (lazy imports:
    importing this module must never import the production stack)."""
    import hybrid_exit_test
    import v54_universe_x2 as ux2

    ux51 = list(hybrid_exit_test.UNIVERSE_X)
    x2 = list(ux2.UNIVERSE_X2)
    themes = {s: "Forward-UX51" for s in ux51} | \
        {s: "Forward-X2" for s in x2}
    return ux51 + x2, themes


class LiveAdapter:
    """The post-GO data path. Never constructed in dry-run/tests."""

    def __init__(self, repo_root: str):
        self.repo_root = repo_root
        self.fetch_calls = 0

    def fetch(self):
        import v54_engine as eng

        self.fetch_calls += 1
        universe, themes = frozen_universe()
        # Market frame FIRST and explicitly: its result decides
        # market_ok. A blind cycle must never read healthy — and
        # (V5 repair) must never SCAN: on market-frame failure
        # (exception, None, or empty) return BEFORE any cohort
        # scan. Scanning 250 names on a blind cycle is pure
        # provider load for data the core will discard as
        # DEGRADED anyway.
        market_ok = False
        try:
            mdf = eng.m53.download_data(
                eng.m53.MARKET_SYMBOL, INTERVAL, PERIOD)
            market_ok = mdf is not None and len(mdf) > 0
        except Exception:
            market_ok = False
        if not market_ok:
            return [], {
                "market_ok": False,
                "scan_complete": False,
                "degraded_symbols": [],
                "expected_symbols": universe,
                "scan_skipped": "MARKET_FRAME_NOT_OK",
            }
        rows, _regime = eng.v54_scan_symbols(
            universe, themes, INTERVAL, PERIOD)
        scanned = {r["symbol"] for r in rows
                   if r.get("state") != "ERROR"}
        scan_complete = all(s in scanned for s in universe)
        degraded = [s for s in universe if s not in scanned]
        candidates = eng.v54_qualified_signals(rows)
        health = {
            "market_ok": market_ok,
            "scan_complete": scan_complete,
            "degraded_symbols": degraded,
            "expected_symbols": universe,
        }
        return candidates, health


class FixtureAdapter:
    """Synthetic adapter for dry-run and tests. fetch() is counted
    so a test can prove the authorization gate fires BEFORE any
    data use, and that one cycle costs exactly one fetch."""

    def __init__(self, candidates, health):
        self.candidates = candidates
        self.health = health
        self.fetch_calls = 0

    def fetch(self):
        self.fetch_calls += 1
        return self.candidates, self.health


def observe_once(repo_root: str, root: str, launch_t0: datetime,
                 adapter, anchor_path: str = None) -> Dict[str, Any]:
    """One cycle: pins first, then observer, then exactly one
    adapter fetch, then the core cycle. Pin failure raises before
    the adapter is touched. When the adapter reports an expected
    universe, it is verified against the core's pinned ordered
    digest before the cycle runs (closeout binding)."""
    verify_pins(repo_root)
    observer = core.SignalObserver(root, launch_t0,
                                   anchor_path=anchor_path)
    candidates, health = adapter.fetch()
    expected = (health or {}).get("expected_symbols")
    if expected is not None:
        core.verify_universe_digest(list(expected))
    return observer.run_cycle(candidates, health)


def _require_launch_authorization(root: str,
                                  launch_t0: datetime) -> None:
    path = os.path.join(root, AUTH_FILENAME)
    if not os.path.exists(path):
        raise core.ShadowError(
            "live mode refused: no LAUNCH_AUTHORIZED.json in the "
            "shadow root. Launch requires Mike's explicit GO naming "
            "a prospective start; this candidate has not been "
            "launched. Use --dry-run for rehearsal.")
    with open(path, encoding="utf-8") as fh:
        auth = json.load(fh)
    auth_t0 = core._parse_ts(auth.get("launch_t0_utc"))
    if auth_t0 is None or auth_t0 != launch_t0:
        raise core.ShadowError(
            "launch authorization T0 does not match the requested "
            "T0 — refusing")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Shadow signal-only observer (candidate; "
                    "not launched)")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--root", default=None,
                    help="shadow namespace directory "
                         "(default: <repo-root>/v54_shadow)")
    ap.add_argument("--t0", default=None,
                    help="prospective launch watermark, ISO 8601 "
                         "tz-aware; frozen at first initialization")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--fixture", default=None,
                    help="dry-run fixture JSON: "
                         "{candidates: [...], health: {...}}")
    ap.add_argument("--verify-log", action="store_true",
                    help="read-only: verify the shadow root's "
                         "hash-chained log against its launch "
                         "manifest and print the anchor report; "
                         "exit 0 if the chain verifies, 2 if not")
    ap.add_argument("--anchor", default=None,
                    help="with --verify-log: external anchor "
                         "JSON {genesis, records, tail_hash}; "
                         "a missing anchor file or a mismatch "
                         "exits 2 (fail-closed)")
    args = ap.parse_args(argv)

    root = args.root or os.path.join(args.repo_root, SHADOW_DIR_NAME)
    if args.verify_log:
        report = core.verify_chain(
            os.path.join(root, core.LOG_FILENAME),
            os.path.join(root, core.MANIFEST_FILENAME))
        if args.anchor:
            try:
                anchor = core.load_anchor_file(args.anchor)
                report["anchor_match"] = core.check_anchor(
                    report, anchor)
            except core.ShadowError as exc:
                report["anchor_match"] = False
                report["failures"].append(str(exc))
            print(json.dumps(report, indent=2, default=str))
            return 0 if report["ok"] and \
                report["anchor_match"] else 2
        print(json.dumps(report, indent=2, default=str))
        return 0 if report["ok"] else 2
    if not args.t0:
        raise core.ShadowError("--t0 is required unless --verify-log")

    launch_t0 = core._parse_ts(args.t0)
    if launch_t0 is None:
        raise core.ShadowError("--t0 must be a tz-aware ISO instant")
    root = args.root or os.path.join(args.repo_root, SHADOW_DIR_NAME)

    if args.dry_run:
        if not args.fixture:
            raise core.ShadowError("--dry-run requires --fixture")
        with open(args.fixture, encoding="utf-8") as fh:
            fixture = json.load(fh)
        adapter = FixtureAdapter(fixture.get("candidates", []),
                                 fixture.get("health", {}))
        # Dry-run verifies pins against the repo when available but
        # never touches the live adapter or the network.
        summary = observe_once(args.repo_root, root, launch_t0,
                               adapter)
    else:
        _require_launch_authorization(root, launch_t0)
        adapter = LiveAdapter(args.repo_root)
        summary = observe_once(args.repo_root, root, launch_t0,
                               adapter)
    print(json.dumps(summary, indent=2, default=str))
    print(f"shadow root: {root}")
    print(f"log: {os.path.join(root, core.LOG_FILENAME)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
