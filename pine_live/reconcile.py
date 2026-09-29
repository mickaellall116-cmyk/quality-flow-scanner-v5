"""Slice 6 — Part-B reconciliation job (docs/PARITY_SPEC.md, Part B).

Replays every live entry/exit packet against the canonical reference and
classifies differences into the seven-category taxonomy from PARITY_SPEC.md
B2. The ONLY passing state is zero category 2-7 mismatches.

Mismatch taxonomy (pipeline layer tells you where the bug lives):
    1 - data_mismatch: same code path, different input bars (Yahoo
        revision, missing bar, download raced a close). Vendor/data cause,
        NOT a logic bug. Counted, digested; a decision-flipping data
        mismatch gets its own digest line.
    2 - bar_construction_mismatch: 4H session boundaries / timezone /
        premarket handling differ on the same raw data. LOGIC BUG.
    3 - indicator_value_mismatch: same bars, different indicator values or
        signal decision. LOGIC BUG.
    4 - ranking_mismatch: rs_score, contested flag, or take/skip differs.
        LOGIC BUG.
    5 - sector_cap_mismatch: sector label, sector count, or skip differs.
        LOGIC BUG.
    6 - state_slot_mismatch: position-slot accounting differs (exits not
        before entries, duplicate signal_id, rerun not idempotent). Also
        covers exit-walk logic (trigger time/price/reason) and strategy
        contamination (e.g. a time-based exit, which V3.6 does not have).
        LOGIC BUG.
    7 - alert_delivery_mismatch: the decision was right but the alert was
        wrong, late, duplicated, or missing. DELIVERY BUG.

Integrity policy: a snapshot whose sha256 does not match, or a snapshot
file that is missing, is a CUSTODY failure, not a category 1-7 difference.
It is reported under "integrity_errors" and ALWAYS fails the run — a
packet that cannot be verified can never pass as "zero mismatches".

V3.6 / V5.4 distinction (pinned): V3.6 has NO time-based exit. The 30-bar
maximum hold belongs to V5.4 Mode B, a different system. The job treats
any exit whose trigger is keyed on elapsed bars/time as a category-6
strategy-contamination mismatch.

Read-only by construction:
  - inputs are file paths + a reference bundle; the job NEVER receives a
    live PortfolioState and never writes to any input file;
  - new modules import only stdlib, pandas, the canonical reference
    (pine_backtest), and the read-only replay/packet helpers;
  - the delivery path (alerts/dedup senders) is never invoked — payloads
    and claims are only READ and compared;
  - the single write is the report JSON into output_dir.

Determinism: every collection is sorted (timestamps, then category, then
signal_id); the report body is canonical JSON. Only meta.generated_at
varies between runs; the "result" section is byte-identical for identical
inputs.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

import pandas as pd

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Read-only reuse only: replay helpers, packet IO, the state machine (for
# throwaway chain states — never the live one), and the canonical
# reference. No import of multicycle/cycle/live_path (the decision path),
# and no import of alert/dedup senders.
import pine_backtest as pb  # noqa: E402
from pine_live.alerts import _PAYLOAD_FIELDS, alert_id_for  # noqa: E402
from pine_live.dedup import dedup_key  # noqa: E402
from pine_live.exits import EXIT_REASONS  # noqa: E402
from pine_live.packets import (  # noqa: E402
    EXIT_PACKET_SCHEMA,
    _canonical,
    load_exit_snapshot,
    load_snapshot,
    read_exit_packets,
)
from pine_live.portfolio import PortfolioState  # noqa: E402
from pine_live.replay import (  # noqa: E402
    replay_exit_decision,
    replay_packet,
    replay_portfolio_decision,
)

CATEGORIES = {
    1: "data_mismatch",
    2: "bar_construction_mismatch",
    3: "indicator_value_mismatch",
    4: "ranking_mismatch",
    5: "sector_cap_mismatch",
    6: "state_slot_mismatch",
    7: "alert_delivery_mismatch",
}
LOGIC_CATEGORIES = {2, 3, 4, 5, 6, 7}

SIGNAL_SCHEMA = "slice1-v1"
PORTFOLIO_SCHEMA = "slice2-v2"

# Clock-only fields: adopted from the packet's pinned pre-state (they
# record engine clock accounting across cycles, including cycles that
# produced no packets). Everything else is re-derived and compared.
CLOCK_FIELDS = {"prev_t", "open_time_s", "total_time_s"}

# Sub-second float noise guard for bar comparisons (snapshots and the
# reference cache both round-trip through JSON/float exactly; anything
# above this is a real revision).
BAR_TOL = 1e-12


def _sha(obj) -> str:
    return hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


def result_digest(result: dict) -> str:
    """Canonical digest of a reconciliation result section (excludes the
    digest field itself so the report is self-verifying)."""
    return _sha({k: v for k, v in result.items() if k != "report_sha256"})


def _read_jsonl(path: str) -> list:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _norm_iso(ts) -> str:
    return pd.Timestamp(ts).isoformat()


def _resolve_snapshot(ref: dict, snapshot_dir: str) -> str:
    """Location-independent snapshot resolution: the packet pins content
    (sha256); the directory supplies location. Lets a copied artifact tree
    reconcile without rewriting packets."""
    return os.path.join(snapshot_dir, os.path.basename(ref["path"]))


def reference_signal_decision(packet: dict,
                              ref_bars: pd.DataFrame) -> bool | None:
    """Recompute the signal decision on the REFERENCE bars at the packet's
    signal bar. Returns True/False, or None when the signal bar is absent
    from the reference frame entirely. Used to tell a genuine vendor
    revision (category 1) apart from a logic flip."""
    try:
        rloc = int(ref_bars.index.get_loc(
            pd.Timestamp(packet["signal_bar_start"])))
    except KeyError:
        return None
    rind = pb.add_pine_indicators(ref_bars)
    return bool(pb.pine_buy_signal(rind, rloc))


def _strip_clock(state: dict) -> dict:
    """State dict minus the clock-only fields (for post-exit
    comparisons: exit packets pin the pre-advance clock by
    construction)."""
    return {k: v for k, v in state.items() if k not in CLOCK_FIELDS}


class Recon:
    """Accumulates one reconciliation run. Use run_reconciliation()."""

    def __init__(self, *, reference: dict, mark_fn, snapshot_dir: str,
                 exit_snapshot_dir: str, timeline: list | None = None):
        for k in ("id", "frames", "trades", "feats", "signal_ids",
                  "signal_index", "taken_by_t", "trade_by_key",
                  "sectors", "cost"):
            if k not in reference:
                raise ValueError(f"reference bundle missing key: {k}")
        self.reference = reference
        self.mark_fn = mark_fn
        self.snapshot_dir = snapshot_dir
        self.exit_snapshot_dir = exit_snapshot_dir
        # Full settlement timeline from the live run's reconciliation
        # manifest (every timestamp the engine visited, including cycles
        # that produced no packets but still settled/marked equity).
        # None -> fall back to packet timestamps (partial runs / drills).
        self.timeline = timeline
        self.mismatches: list = []
        self.integrity_errors: list = []
        self.cat1_digest: list = []
        self.custody: list = []
        self.notes: list = []
        self.counts = {"n_signal_packets": 0, "n_portfolio_packets": 0,
                       "n_exit_packets": 0}
        # Symbols whose pinned bars differ from the reference bars
        # (category 1). Reference comparisons for these symbols are
        # skipped: any downstream price/score difference is a consequence
        # of the data difference, not an independent logic bug. The
        # signal-level replay on the packet's OWN bars still applies —
        # correct code on the actual bars is always required.
        self.data_symbols: set = set()

    # -- recording -----------------------------------------------------
    def mismatch(self, *, category: int, layer: str, timestamp: str,
                 signal_id: str | None, packet: dict, detail):
        self.mismatches.append({
            "category": category,
            "category_name": CATEGORIES[category],
            "layer": layer,
            "timestamp": timestamp,
            "signal_id": signal_id,
            "packet_sha256": _sha(packet),
            "detail": detail,
        })

    def integrity(self, *, kind: str, timestamp: str, signal_id: str | None,
                  packet: dict | None, detail: str):
        self.integrity_errors.append({
            "kind": kind,
            "timestamp": timestamp,
            "signal_id": signal_id,
            "packet_sha256": _sha(packet) if packet is not None else None,
            "detail": detail,
        })

    def data(self, *, timestamp: str, signal_id: str, symbol: str,
             packet: dict, cause: str, detail: dict):
        entry = {"category": 1, "category_name": CATEGORIES[1],
                 "timestamp": timestamp, "signal_id": signal_id,
                 "symbol": symbol,
                 "packet_sha256": _sha(packet), "cause": cause,
                 "detail": detail}
        self.cat1_digest.append(entry)

    def custody_record(self, *, kind: str, packet: dict) -> None:
        """Pin the custody hashes for one reconciled packet: the packet
        itself, its pinned bar snapshot (if any), and its pinned
        pre/post states (exit packets only — portfolio packets pin
        decision observables, signal packets pin no state)."""
        if kind == "signal":
            timestamp = packet.get("signal_bar_start") or ""
        else:
            timestamp = _norm_iso(packet["decision_time"])
        snap_ref = packet.get("bars_snapshot_ref") or {}
        rec = {
            "kind": kind,
            "timestamp": timestamp,
            "signal_id": packet.get("signal_id"),
            "packet_sha256": _sha(packet),
            "snapshot_sha256": snap_ref.get("sha256"),
            "pre_state_sha256": None,
            "post_state_sha256": None,
        }
        if kind == "exit":
            rec["pre_state_sha256"] = _sha(packet["pre_exit_state"])
            rec["post_state_sha256"] = _sha(packet["post_exit_state"])
        self.custody.append(rec)

    # -- signal level --------------------------------------------------
    def reconcile_signals(self, sig_packets: list) -> None:
        ref = self.reference
        decided = [p for p in sig_packets if p.get("decision") != "refused"]
        n_refused = len(sig_packets) - len(decided)
        if n_refused:
            # Refusals mean the live path declined to decide (fail-closed);
            # there is no decision to reconcile. Counted, never ignored.
            self.notes.append({"refused_signal_packets_skipped": n_refused})
        for p in sorted(decided, key=lambda q: (q["signal_bar_start"],
                                                q["signal_id"])):
            self.counts["n_signal_packets"] += 1
            self.custody_record(kind="signal", packet=p)
            t_disp = p["signal_bar_start"]
            sid = p["signal_id"]
            symbol = p["symbol"]
            snap_path = _resolve_snapshot(p["bars_snapshot_ref"],
                                          self.snapshot_dir)
            try:
                rep = replay_packet(dict(p, bars_snapshot_ref=dict(
                    p["bars_snapshot_ref"], path=snap_path)))
            except Exception as exc:  # noqa: BLE001 — hash failure etc.
                self.integrity(kind="signal_snapshot_unreadable",
                               timestamp=t_disp, signal_id=sid, packet=p,
                               detail=f"{type(exc).__name__}: {exc} "
                                      f"(snapshot {snap_path})")
                continue
            if not rep["replayed"]:
                self.integrity(kind="signal_replay_impossible",
                               timestamp=t_disp, signal_id=sid, packet=p,
                               detail=rep["reason"])
                continue
            if rep["price_diffs"]:
                self.mismatch(category=2, layer="signal",
                              timestamp=t_disp, signal_id=sid, packet=p,
                              detail={"price_diffs": rep["price_diffs"]})
            if rep["indicator_diffs"]:
                self.mismatch(category=3, layer="signal",
                              timestamp=t_disp, signal_id=sid, packet=p,
                              detail={"indicator_diffs": rep["indicator_diffs"]})
            if not rep["decision_match"]:
                self.mismatch(
                    category=3, layer="signal",
                    timestamp=t_disp, signal_id=sid, packet=p,
                    detail={"packet_decision": rep["packet_decision"],
                            "recomputed_decision":
                                rep["recomputed_decision"]})

            # Vendor / data comparison: the packet's pinned bars vs the
            # reference bars for the same symbol and bar range.
            try:
                snap = load_snapshot(snap_path,
                                     p["bars_snapshot_ref"]["sha256"])
            except Exception as exc:  # noqa: BLE001
                self.integrity(kind="signal_snapshot_unreadable",
                               timestamp=t_disp, signal_id=sid, packet=p,
                               detail=f"{type(exc).__name__}: {exc}")
                continue
            ref_bars = ref["frames"].get(symbol)
            if ref_bars is None:
                raise ValueError(
                    f"reconcile: no reference bars for {symbol}")
            try:
                ref_slice = ref_bars.loc[snap.index]
            except KeyError:
                ref_slice = None
            bars_differ = False
            diff_detail: dict = {}
            if ref_slice is None or len(ref_slice) != len(snap):
                bars_differ = True
                diff_detail = {"cause": "bar_coverage_differs",
                               "snapshot_bars": len(snap),
                               "reference_bars":
                                   None if ref_slice is None
                                   else len(ref_slice)}
            else:
                bad_cols = [
                    c for c in ("Open", "High", "Low", "Close", "Volume")
                    if (abs(ref_slice[c].to_numpy(dtype=float)
                            - snap[c].to_numpy(dtype=float)) > BAR_TOL).any()
                ]
                if bad_cols:
                    bars_differ = True
                    diff_detail = {"cause": "vendor_revision",
                                   "columns": bad_cols}
            if bars_differ:
                # Did the different bars flip the decision? Recompute the
                # signal on the REFERENCE bars at the same signal bar.
                ref_decision = reference_signal_decision(p, ref_bars)
                flipped = (None if ref_decision is None
                           else ref_decision != (p["decision"] == "signal"))
                self.data_symbols.add(symbol)
                self.data(timestamp=t_disp, signal_id=sid, symbol=symbol,
                          packet=p,
                          cause=diff_detail["cause"],
                          detail={**diff_detail,
                                  "decision_flipped": flipped})

    def reconcile_signal_set(self, sig_packets: list) -> None:
        live_ids = {p["signal_id"] for p in sig_packets
                    if p.get("decision") == "signal"}
        ref_ids = set(self.reference["signal_ids"])
        for sid in sorted(ref_ids - live_ids):
            self.mismatch(category=2, layer="signal-set",
                          timestamp="", signal_id=sid, packet={},
                          detail="reference signal has no live signal packet")
        for sid in sorted(live_ids - ref_ids):
            self.mismatch(category=2, layer="signal-set",
                          timestamp="", signal_id=sid, packet={},
                          detail="live signal has no reference signal")

    # -- portfolio + exit chain ----------------------------------------
    def _check_pre_state(self, packet: dict, chain: PortfolioState,
                         t_iso: str, clock: bool = True) -> None:
        """Compare the exit packet's pinned pre-state against the re-derived
        chain state. The chain is pre-advance here, exactly as the packet
        pins it (pre_timestamp_state is captured before advance_clock in
        the live path). Clock-only fields are adopted from the packet as a
        fail-safe; every economic field must match exactly.

        clock=False: econ-only check for the 2nd+ exit at a timestamp —
        those packets pin the pre-advance clock, but the chain has
        advanced by then (their sequential pre-states are still pinned
        economically)."""
        pre = packet["pre_exit_state"]
        cur = chain.to_dict()
        econ_keys = [k for k in pre if k not in CLOCK_FIELDS]
        diffs = {k: {"packet": pre[k], "chain": cur.get(k)}
                 for k in econ_keys if pre[k] != cur.get(k)}
        if diffs:
            self.mismatch(category=6, layer="exit-chain",
                          timestamp=t_iso,
                          signal_id=packet.get("signal_id"),
                          packet=packet, detail={"pre_state_diffs": diffs})
        if not clock:
            return
        adopted = {k: pre[k] for k in CLOCK_FIELDS if cur.get(k) != pre[k]}
        if adopted:
            cur2 = chain.to_dict()
            for k, v in adopted.items():
                cur2[k] = v
            # apply adoption through from_dict round-trip to keep the
            # object internally consistent
            restored = PortfolioState.from_dict(cur2, self.mark_fn)
            chain.__dict__.clear()
            chain.__dict__.update(restored.__dict__)
            self.notes.append({"clock_adopted": True, "timestamp": t_iso,
                               "fields": sorted(adopted)})

    def _chain_timeline(self, port_by_t: dict, exits_by_t: dict) -> list:
        """The settlement timeline the chain must walk.

        With the live run's reconciliation manifest: the manifest's
        timeline — every timestamp the engine visited, including
        no-packet settlement cycles that still mark equity and move
        peak/max_drawdown. Cross-checked against the packets and the
        reference window; any gap is an integrity error, never silently
        papered over.

        Without a manifest (partial runs, single-cycle drills): packet
        timestamps, with a note recording the fallback.
        """
        pkt_times = set(port_by_t) | set(exits_by_t)
        if self.timeline is None:
            self.notes.append({
                "timeline": "manifest_absent_fallback_to_packet_timestamps",
                "note": "no-packet settlement cycles cannot be replayed; "
                        "peak/max_drawdown are pinned only at packeted "
                        "timestamps"})
            return sorted(pkt_times, key=lambda s: pd.Timestamp(s))
        manifest_times = sorted(self.timeline,
                                key=lambda s: pd.Timestamp(s))
        mset = set(manifest_times)
        for t in sorted(pkt_times - mset):
            self.integrity(kind="packet_timestamp_not_in_manifest",
                           timestamp=t, signal_id=None, packet=None,
                           detail="a packet exists for a timestamp the "
                                  "live run's manifest never visited")
        ref = self.reference
        ref_times = ({_norm_iso(tr["entry_time"]) for tr in ref["trades"]} |
                     {_norm_iso(tr["exit_time"]) for tr in ref["trades"]})
        for t in sorted(ref_times - mset):
            self.integrity(kind="manifest_missing_reference_timestamp",
                           timestamp=t, signal_id=None, packet=None,
                           detail="the live run's manifest skips a "
                                  "reference entry/exit timestamp: its "
                                  "settlements are unaccounted for")
        extra = sorted(mset - ref_times)
        if extra:
            self.notes.append({"manifest_extra_timestamps": extra})
        return manifest_times

    def reconcile_chain(self, portfolio_packets: list,
                        exit_packets: list) -> None:
        ref = self.reference
        port_by_t = {}
        for p in portfolio_packets:
            port_by_t.setdefault(_norm_iso(p["decision_time"]), []).append(p)
            self.custody_record(kind="portfolio", packet=p)
        exits_by_t: dict = {}
        for p in exit_packets:
            exits_by_t.setdefault(_norm_iso(p["decision_time"]), []).append(p)
            self.custody_record(kind="exit", packet=p)
        all_t = self._chain_timeline(port_by_t, exits_by_t)

        chain = PortfolioState(self.mark_fn, ref["cost"])
        for t_iso in all_t:
            t = pd.Timestamp(t_iso)
            exits = exits_by_t.get(t_iso, [])
            # 0. full pre-state check for the first exit. The chain is
            #    pre-advance here, exactly as the packet pins it — this
            #    pins the clock. (2nd+ exits at this timestamp get
            #    econ-only pre-checks inside the loop below: their
            #    packets pin sequential pre-states with the pre-advance
            #    clock, but the chain has advanced by then.)
            if exits:
                self._check_pre_state(exits[0], chain, t_iso)
            # 1. clock advance — live order. advance_clock runs inside
            #    run_timestamp BEFORE exits are applied, so open_time
            #    accrues on the positions carried into t. (process_exits
            #    and advance_clock are NOT disjoint: the accrual reads
            #    the position book, so this ordering is load-bearing.)
            chain.advance_clock(t)
            # 2. exits sequentially, in packet/file order (the live path
            #    writes them sorted by symbol).
            for j, p in enumerate(exits):
                self.counts["n_exit_packets"] += 1
                sid = p.get("signal_id")
                if j > 0:
                    self._check_pre_state(p, chain, t_iso, clock=False)
                # 1a. replay the walk from the packet's own snapshot
                epath = _resolve_snapshot(p["bars_snapshot_ref"],
                                          self.exit_snapshot_dir)
                p2 = dict(p, bars_snapshot_ref=dict(
                    p["bars_snapshot_ref"], path=epath))
                try:
                    rep = replay_exit_decision(
                        p2, snapshot_dir=self.exit_snapshot_dir)
                except Exception as exc:  # noqa: BLE001
                    self.integrity(kind="exit_snapshot_unreadable",
                                   timestamp=t_iso, signal_id=sid, packet=p,
                                   detail=f"{type(exc).__name__}: {exc}")
                    rep = None
                if rep is None:
                    pass  # integrity already recorded above
                elif not rep.get("replayed"):
                    reason = rep.get("reason", "unknown")
                    kind = ("exit_snapshot_tampered"
                            if ("snapshot rejected" in reason
                                or "hash" in reason)
                            else "exit_replay_impossible")
                    self.integrity(kind=kind,
                                   timestamp=t_iso, signal_id=sid,
                                   packet=p, detail=reason)
                elif not rep["exact"]:
                    self.mismatch(category=6, layer="exit-walk",
                                  timestamp=t_iso, signal_id=sid, packet=p,
                                  detail={"diffs": rep["diffs"]})
                # 1b. strategy-contamination guard: V3.6 has no time exit
                reason = (p.get("trigger") or {}).get("reason")
                if reason not in EXIT_REASONS:
                    self.mismatch(
                        category=6, layer="strategy-contamination",
                        timestamp=t_iso, signal_id=sid, packet=p,
                        detail={"reason": reason,
                                "allowed": list(EXIT_REASONS),
                                "note": "V3.6 has no time-based exit; the "
                                        "30-bar max hold is V5.4 Mode B"})
                # 1c. against the reference trade
                key = (p["symbol"], p["position"]["entry_time"])
                tr = ref["trade_by_key"].get(key)
                if tr is None:
                    self.mismatch(category=6, layer="exit-vs-reference",
                                  timestamp=t_iso, signal_id=sid, packet=p,
                                  detail="no reference trade for "
                                         f"{key}")
                else:
                    exp = p.get("exit") or {}
                    trig = p.get("trigger") or {}
                    for pk, tk in (("exit_px", "exit"),
                                   ("reason", "reason"),
                                   ("tp1_hit", "tp1_hit"),
                                   ("hold_bars", "hold_bars")):
                        got = (trig if pk in ("reason", "tp1_hit")
                               else exp).get(pk)
                        want = tr[tk]
                        same = (abs(got - want) < 1e-12
                                if isinstance(want, float) else got == want)
                        if not same:
                            self.mismatch(
                                category=6, layer="exit-vs-reference",
                                timestamp=t_iso, signal_id=sid, packet=p,
                                detail={pk: {"packet": got,
                                             "reference": want}})
                # 1d. apply to the chain; the economic post-state must
                #     match exactly. (The packet's post pins the
                #     PRE-advance clock by construction — it is derived
                #     from pre_timestamp_state — so clock fields are
                #     excluded here; they were pinned by the pre-state
                #     check in step 0.)
                ev = {"symbol": p["symbol"],
                      "exit_px": float(p["exit"]["exit_px"]),
                      "reason": reason, "universe_order": 0}
                chain.process_exits(t, [ev])
                post = chain.to_dict()
                if (_strip_clock(post)
                        != _strip_clock(p["post_exit_state"])):
                    self.mismatch(
                        category=6, layer="exit-chain",
                        timestamp=t_iso, signal_id=sid, packet=p,
                        detail="chain post-exit state != packet "
                               "post_exit_state")
            # 3. portfolio decision
            pkts = port_by_t.get(t_iso, [])
            if pkts:
                pkt = pkts[0]
                if len(pkts) > 1:
                    self.mismatch(category=6, layer="portfolio-log",
                                  timestamp=t_iso, signal_id=None,
                                  packet=pkt,
                                  detail=f"{len(pkts)} portfolio packets "
                                         "at one timestamp")
                self.counts["n_portfolio_packets"] += 1
                self._reconcile_portfolio_packet(pkt, chain, t)
                contenders = [self._chain_contender(c)
                              for c in pkt["contenders"]]
                chain.decide_entries(t, contenders)
            chain.settle(t)

    def _chain_contender(self, c: dict) -> dict:
        """Build the contender the settlement chain replays.

        Ranking features come from the reference (ground truth), never
        from the packet's claims: the packet's claimed rs_score is what
        section 3b audits (a tampered claim is a clean category-4), and
        letting a tampered claim into the chain would poison every
        downstream state comparison with cascade noise (the tampered
        score leaks into the open-event log, so later exit packets'
        pinned states stop matching). The one exception is a category-1
        symbol, whose bars genuinely differ (vendor revision): there the
        reference features cannot reproduce what the engine computed, so
        the packet's claimed score — the engine's true value on the
        revised bars — is kept.
        """
        rs = c["rs_score"]
        if c["symbol"] not in self.data_symbols:
            idx = self.reference["signal_index"].get(c["signal_id"])
            if idx is not None:
                rs = float(self.reference["feats"][idx]["rs"])
        return {"signal_id": c["signal_id"], "symbol": c["symbol"],
                "entry_px": c["entry_px"], "stop_px": c["stop_px"],
                "tp1_px": c["tp1_px"], "rs_score": rs,
                "universe_order": c["universe_order"]}

    def _reconcile_portfolio_packet(self, pkt: dict, chain: PortfolioState,
                                    t) -> None:
        ref = self.reference
        t_iso = _norm_iso(pkt["decision_time"])
        # 3a. replay the decision from the chained prior state
        rep = replay_portfolio_decision(pkt, chain.to_dict(), self.mark_fn)
        if not rep["replayed"]:
            if rep.get("reason") == "state-before mismatch":
                self.mismatch(category=6, layer="state-chain",
                              timestamp=t_iso, signal_id=None, packet=pkt,
                              detail={"pre_diffs": rep.get("pre_diffs")})
            else:
                self.mismatch(category=6, layer="portfolio-replay",
                              timestamp=t_iso, signal_id=None, packet=pkt,
                              detail={"reason": rep.get("reason")})
            return
        for d in rep["diffs"]:
            sid = d.get("signal_id")
            if "order" in d:
                cat = 6
            elif "rs_score" in d or "rank" in d or "contested" in d:
                cat = 4
            elif "decision" in d or "reason_detail" in d:
                pkt_dec = next(
                    (x["decision"] for x in pkt["decisions"]
                     if x["signal_id"] == sid), None)
                cat = {"RANKED_OUT": 4, "SECTOR_CAP": 5}.get(pkt_dec, 6)
            else:
                cat = 6  # marked_equity_at_t, sector_counts_after, ...
            self.mismatch(category=cat, layer="portfolio-replay",
                          timestamp=t_iso, signal_id=sid, packet=pkt,
                          detail=d)
        # 3b. contenders vs the reference candidate set
        # (skipped for category-1 symbols: their reference comparison is
        # meaningless once the bars are known to differ)
        data_contenders = [c["symbol"] for c in pkt["contenders"]
                           if c["symbol"] in self.data_symbols]
        if data_contenders:
            self.notes.append(
                {"reference_comparison_skipped": sorted(data_contenders),
                 "timestamp": t_iso,
                 "reason": "category-1 bar difference"})
        for c in pkt["contenders"]:
            if c["symbol"] in self.data_symbols:
                continue
            sid = c["signal_id"]
            idx = ref["signal_index"].get(sid)
            if idx is None:
                continue  # covered by the signal-set check
            tr = ref["trades"][idx]
            if abs(c["rs_score"] - float(ref["feats"][idx]["rs"])) > 1e-12:
                self.mismatch(category=4, layer="ranking",
                              timestamp=t_iso, signal_id=sid, packet=pkt,
                              detail={"rs_score": {
                                  "packet": c["rs_score"],
                                  "reference": float(
                                      ref["feats"][idx]["rs"])}})
            for pk, tk in (("entry_px", "entry"), ("stop_px", "stop"),
                           ("tp1_px", "tp1")):
                if abs(c[pk] - float(tr[tk])) > 1e-12:
                    self.mismatch(category=2, layer="contender-prices",
                                  timestamp=t_iso, signal_id=sid, packet=pkt,
                                  detail={pk: {"packet": c[pk],
                                               "reference": float(tr[tk])}})
            if c["sector"] != ref["sectors"].get(c["symbol"]):
                self.mismatch(category=5, layer="sector-label",
                              timestamp=t_iso, signal_id=sid, packet=pkt,
                              detail={"sector": {
                                  "packet": c["sector"],
                                  "reference": ref["sectors"].get(
                                      c["symbol"])}})
        # 3c. taken set vs the reference taken set at this timestamp
        # (skipped when a category-1 symbol contends: its data difference
        # could legitimately move the take/skip line)
        if data_contenders:
            return
        live_taken = {d["signal_id"] for d in pkt["decisions"]
                      if d["decision"] == "TAKEN"}
        ref_taken = set(ref["taken_by_t"].get(t_iso, []))
        for sid in sorted(live_taken ^ ref_taken):
            d = next((x for x in pkt["decisions"]
                      if x["signal_id"] == sid), None)
            reason = d["decision"] if d else "missing_from_packet"
            cat = {"RANKED_OUT": 4, "SECTOR_CAP": 5}.get(reason, 6)
            self.mismatch(category=cat, layer="taken-set",
                          timestamp=t_iso, signal_id=sid, packet=pkt,
                          detail={"live_taken": sid in live_taken,
                                  "reference_taken": sid in ref_taken,
                                  "packet_decision": reason})

    # -- delivery ------------------------------------------------------
    def reconcile_delivery(self, portfolio_packets: list,
                           outbox_path: str | None,
                           dedup_path: str | None) -> None:
        if outbox_path is None and dedup_path is None:
            self.notes.append({"delivery": "not_configured_skipped"})
            return
        queued: dict = {}
        if outbox_path:
            for ev in _read_jsonl(outbox_path):
                if ev.get("event") == "alert_queued":
                    queued[ev["alert_id"]] = ev["payload"]
        claimed: set = set()
        if dedup_path:
            for rec in _read_jsonl(dedup_path):
                if rec.get("event") == "claimed":
                    claimed.add(rec["key"])
        expected_aids: set = set()
        expected_keys: set = set()
        for pkt in portfolio_packets:
            t_iso = pkt["decision_time"]  # as stored (matches dedup_key input)
            seq_after = pkt["state_event_log_range"][1]
            for d in pkt["decisions"]:
                key = dedup_key(d["signal_id"], t_iso, seq_after)
                expected_keys.add(key)
                if key not in claimed:
                    self.mismatch(category=7, layer="delivery",
                                  timestamp=t_iso,
                                  signal_id=d["signal_id"], packet=pkt,
                                  detail="finalized decision has no dedup "
                                         "claim")
                if d["decision"] == "TAKEN":
                    aid = alert_id_for(d["signal_id"], t_iso)
                    expected_aids.add(aid)
                    payload = queued.get(aid)
                    if payload is None:
                        self.mismatch(category=7, layer="delivery",
                                      timestamp=t_iso,
                                      signal_id=d["signal_id"], packet=pkt,
                                      detail="TAKEN decision has no queued "
                                             "alert")
                        continue
                    for pkey, src in _PAYLOAD_FIELDS:
                        want = (pkt["decision_time"]
                                if src == "@decision_time" else d[src])
                        if payload.get(pkey) != want:
                            self.mismatch(
                                category=7, layer="delivery",
                                timestamp=t_iso, signal_id=d["signal_id"],
                                packet=pkt,
                                detail={"payload_field": pkey,
                                        "payload": payload.get(pkey),
                                        "packet": want})
        for aid in sorted(set(queued) - expected_aids):
            self.mismatch(category=7, layer="delivery",
                          timestamp="", signal_id=queued[aid].get("signal_id"),
                          packet={},
                          detail=f"unexpected alert {aid}: no matching "
                                 "TAKEN decision")
        for key in sorted(claimed - expected_keys):
            self.mismatch(category=7, layer="delivery",
                          timestamp="", signal_id=None, packet={},
                          detail=f"unexpected dedup claim {key}")


def _load_manifest(path: str | None) -> list | None:
    """Load the live run's reconciliation manifest (causally-inert
    artifact written by the run harness): the full ordered settlement
    timeline. Returns the timeline list, or None when no manifest was
    supplied. Raises ValueError for a malformed manifest — a corrupt
    custody artifact can never silently fall back."""
    if path is None:
        return None
    if not os.path.exists(path):
        raise ValueError(f"reconcile: manifest not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    if manifest.get("manifest_schema") != "recon-manifest-v1":
        raise ValueError(
            f"reconcile: bad manifest schema in {path}: "
            f"{manifest.get('manifest_schema')!r}")
    timeline = manifest.get("timeline")
    if not isinstance(timeline, list) or not timeline:
        raise ValueError(f"reconcile: manifest has no timeline: {path}")
    return [_norm_iso(t) for t in timeline]


def run_reconciliation(*, packet_log: str, exit_packet_log: str,
                       snapshot_dir: str, exit_snapshot_dir: str | None = None,
                       outbox_path: str | None = None,
                       dedup_path: str | None = None,
                       manifest_path: str | None = None,
                       reference: dict, mark_fn,
                       output_dir: str, now=None) -> dict:
    """Run the Part-B reconciliation job. Read-only w.r.t. all inputs.

    Returns the report dict and writes it (fsync'd) to
    output_dir/reconciliation_report.json. Raises only for configuration
    errors (missing files, malformed reference bundle) — never for
    mismatches (those are the report's content).
    """
    for label, path in (("packet_log", packet_log),
                        ("exit_packet_log", exit_packet_log),
                        ("snapshot_dir", snapshot_dir)):
        if not os.path.exists(path):
            raise ValueError(f"reconcile: {label} not found: {path}")
    exit_snapshot_dir = exit_snapshot_dir or snapshot_dir
    os.makedirs(output_dir, exist_ok=True)

    records = _read_jsonl(packet_log)
    sig_packets = [r for r in records
                   if r.get("packet_schema") == SIGNAL_SCHEMA
                   and "signal_id" in r]
    portfolio_packets = [r for r in records
                         if r.get("packet_schema") == PORTFOLIO_SCHEMA]
    exit_packets = read_exit_packets(exit_packet_log)
    exit_packets = [p for p in exit_packets
                    if p.get("packet_schema") == EXIT_PACKET_SCHEMA]

    recon = Recon(reference=reference, mark_fn=mark_fn,
                  snapshot_dir=snapshot_dir,
                  exit_snapshot_dir=exit_snapshot_dir,
                  timeline=_load_manifest(manifest_path))
    recon.reconcile_signals(sig_packets)
    recon.reconcile_signal_set(sig_packets)
    recon.reconcile_chain(portfolio_packets, exit_packets)
    recon.reconcile_delivery(portfolio_packets, outbox_path, dedup_path)

    mismatches = sorted(recon.mismatches,
                        key=lambda m: (m["timestamp"], m["category"],
                                       m["layer"], m["signal_id"] or ""))
    integrity = sorted(recon.integrity_errors,
                       key=lambda e: (e["timestamp"], e["kind"],
                                      e["signal_id"] or ""))
    cat1 = sorted(recon.cat1_digest,
                  key=lambda e: (e["timestamp"], e["signal_id"] or ""))

    counts = {str(c): sum(1 for m in mismatches if m["category"] == c)
              for c in range(2, 8)}
    # Category 1 lives in its own digest (data/vendor cause, not a logic
    # mismatch); its count is the digest length by construction.
    counts["1"] = len(cat1)
    custody = sorted(recon.custody,
                     key=lambda r: (r["timestamp"], r["kind"],
                                    r["signal_id"] or ""))
    logic_bad = any(m["category"] in LOGIC_CATEGORIES for m in mismatches)
    verdict = "PASS" if (not logic_bad and not integrity) else "FAIL"
    # First divergence: earliest (timestamp, kind, category, layer,
    # signal_id). Mismatches sort before integrity errors at the same
    # timestamp. Deterministic by construction.
    cands = []
    for m in mismatches:
        if m["category"] in LOGIC_CATEGORIES:
            cands.append({"timestamp": m["timestamp"],
                          "signal_id": m["signal_id"],
                          "category": m["category"], "layer": m["layer"],
                          "kind": "mismatch"})
    for e in integrity:
        if e["timestamp"]:
            cands.append({"timestamp": e["timestamp"],
                          "signal_id": e["signal_id"],
                          "category": None, "layer": e["kind"],
                          "kind": "integrity"})
    cands.sort(key=lambda c: (c["timestamp"],
                              0 if c["kind"] == "mismatch" else 1,
                              c["category"] or 0, c["layer"],
                              c["signal_id"] or ""))
    first_divergence = cands[0] if cands else None

    from datetime import datetime, timezone
    result = {
        "verdict": verdict,
        "reference": reference["id"],
        "n_signal_packets": recon.counts["n_signal_packets"],
        "n_portfolio_packets": recon.counts["n_portfolio_packets"],
        "n_exit_packets": recon.counts["n_exit_packets"],
        "counts_by_category": counts,
        "n_category_1": len(cat1),
        "n_integrity_errors": len(integrity),
        "n_custody_records": len(custody),
        "first_divergence": first_divergence,
        "mismatches": mismatches,
        "integrity_errors": integrity,
        "digest_category_1": cat1,
        "custody": custody,
        "notes": sorted(recon.notes, key=_canonical),
    }
    result["report_sha256"] = result_digest(result)
    report = {
        "report_schema": "recon-v1",
        "meta": {
            "generated_at": (now if now is not None else datetime.now(
                timezone.utc)).isoformat()
            if not isinstance(now, str) else now,
            "inputs": {
                "packet_log": packet_log,
                "exit_packet_log": exit_packet_log,
                "snapshot_dir": snapshot_dir,
                "exit_snapshot_dir": exit_snapshot_dir,
                "outbox_path": outbox_path,
                "dedup_path": dedup_path,
                "manifest_path": manifest_path,
            },
        },
        "result": result,
    }
    out_path = os.path.join(output_dir, "reconciliation_report.json")
    body = _canonical(report)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(body + "\n")
        f.flush()
        os.fsync(f.fileno())
    report["report_path"] = out_path
    return report
