#!/usr/bin/env python3
"""
forward_scoreboard.py — live forward-test scoreboard for the Quality Flow
confirmatory research program (mandate: research_notes/research_mandate.md).

READ-ONLY. This script only reads the frozen forward-test log and the paper
sidecar logs. It never writes to them, never touches the forward-test harness,
V5.4, Mode B, production alerts, grades, market gate, or the AI Observer.

Tracks: V5.4 baseline | FVG paper sidecar | lone-wolf paper overlay |
ADX ranking shadow (if feasible).

Usage:
    python3 forward_scoreboard.py            # plain-text scoreboard
    python3 forward_scoreboard.py --json     # same data as JSON

The sample-size warning is mandatory on every run: never declare a winner
from a tiny live sample.
"""

import argparse
import json
import os
import sys
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
FWD = os.path.join(BASE, "v54_forward")
FWD_LOG = os.path.join(FWD, "forward_test.jsonl")
FVG_LOG = os.path.join(FWD, "fvg_sidecar.jsonl")
LW_LOG = os.path.join(FWD, "lonewolf_overlay.jsonl")

# Portfolio slot cap used by the forward-test admission logic.
SLOT_CAP = 5


def read_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def fmt(x, nd=3):
    if x is None:
        return "n/a"
    if isinstance(x, float):
        return f"{x:+.{nd}f}" if nd else str(x)
    return str(x)


def stats_for(closed_rs):
    """closed_rs: list of blended R values (floats)."""
    n = len(closed_rs)
    if n == 0:
        return {
            "closed": 0, "expectancy_r": None, "win_rate": None,
            "profit_factor": None, "wins": 0, "losses": 0,
        }
    wins = [r for r in closed_rs if r > 0]
    losses = [r for r in closed_rs if r <= 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    pf = (gross_win / gross_loss) if gross_loss > 0 else (float("inf") if gross_win > 0 else None)
    return {
        "closed": n,
        "expectancy_r": round(sum(closed_rs) / n, 4),
        "win_rate": round(len(wins) / n, 4),
        "profit_factor": round(pf, 3) if pf not in (None, float("inf")) else ("inf" if pf == float("inf") else None),
        "wins": len(wins),
        "losses": len(losses),
    }


def size_warning(n_closed, label="closed trades"):
    if n_closed == 0:
        return f"n=0 {label} — no outcomes yet, do not judge"
    if n_closed < 10:
        return f"n={n_closed} {label} — noise, do not judge"
    if n_closed < 30:
        return f"n={n_closed} {label} — thin, treat as directional only"
    return f"n={n_closed} {label} — modest sample, still early"


# ---------------------------------------------------------------- baseline
def baseline_board():
    rows = read_jsonl(FWD_LOG)
    signals = {}
    closes = {}          # signal_id -> close record (type 'close' or 'closed' event)
    opened = set()
    skipped = 0
    for r in rows:
        t = r.get("type")
        if t == "signal":
            signals[r["signal_id"]] = r
        elif t == "close":
            closes[r["signal_id"]] = r
        elif t == "event":
            ev = r.get("event")
            if ev == "opened":
                opened.add(r["signal_id"])
            elif ev == "signal_skipped":
                skipped += 1
            elif ev == "closed" and r["signal_id"] not in closes:
                closes[r["signal_id"]] = r  # fallback if no 'close' record

    closed_rs = [float(c["blended_r"]) for c in closes.values()
                 if c.get("blended_r") is not None]
    st = stats_for(closed_rs)
    maes = [float(c["mae_r"]) for c in closes.values() if c.get("mae_r") is not None]
    mfes = [float(c["mfe_r"]) for c in closes.values() if c.get("mfe_r") is not None]
    open_now = len(opened) - len(closes)

    return {
        "name": "V5.4 baseline (frozen)",
        "signals_seen": len(signals),
        "signals_skipped": skipped,
        "opened": len(opened),
        "open_now": open_now,
        "closed_trades": st["closed"],
        "expectancy_r": st["expectancy_r"],
        "win_rate": st["win_rate"],
        "profit_factor": st["profit_factor"],
        "worst_mae_r": round(min(maes), 4) if maes else None,
        "best_mfe_r": round(max(mfes), 4) if mfes else None,
        "mfe_mae_note": "logged on forward-test close records" if maes else "not logged",
        "missed_winners": "n/a (baseline takes all signals)",
        "avoided_losers": "n/a (baseline takes all signals)",
        "sample_warning": size_warning(st["closed"]),
    }, signals, closes


# ---------------------------------------------------------------- FVG sidecar
def fvg_board():
    rows = read_jsonl(FVG_LOG)
    signals = {}
    opened = set()
    closes = {}
    skipped = 0
    for r in rows:
        t = r.get("type")
        if t == "signal":
            signals[r["signal_id"]] = r
        elif t == "event":
            ev = r.get("event")
            if ev == "opened":
                opened.add(r["signal_id"])
            elif ev == "closed":
                closes[r["signal_id"]] = r
            elif ev == "signal_skipped":
                skipped += 1
    # FVG variant closes (if the sidecar ever logs 'close'-type records)
    closed_rs = [float(c["blended_r"]) for c in closes.values()
                 if c.get("blended_r") is not None]
    st = stats_for(closed_rs)
    return {
        "name": "FVG paper sidecar (hybrid+fvg-entry)",
        "signals_seen": len(signals),
        "signals_skipped": skipped,
        "opened": len(opened),
        "open_now": len(opened) - len(closes),
        "closed_trades": st["closed"],
        "expectancy_r": st["expectancy_r"],
        "win_rate": st["win_rate"],
        "profit_factor": st["profit_factor"],
        "worst_mae_r": None,
        "best_mfe_r": None,
        "mfe_mae_note": "not logged by FVG sidecar yet",
        "missed_winners": "n/a (entry variant, not a filter)",
        "avoided_losers": "n/a (entry variant, not a filter)",
        "sample_warning": size_warning(st["closed"]),
    }


# ---------------------------------------------------------------- lone-wolf overlay
def lonewolf_board(fwd_closes):
    rows = read_jsonl(LW_LOG)
    overlays = {}   # signal_id -> signal_overlay
    blocked_ids = set()
    mapped = 0
    for r in rows:
        if r.get("type") == "signal_overlay":
            overlays[r["signal_id"]] = r
            if r.get("would_block"):
                blocked_ids.add(r["signal_id"])
            if r.get("reason") != "no_sector_mapping":
                mapped += 1
    # Join blocked signals to baseline outcomes
    blocked_rs, allowed_rs = [], []
    for sid, ov in overlays.items():
        c = fwd_closes.get(sid)
        if c is None or c.get("blended_r") is None:
            continue
        (blocked_rs if sid in blocked_ids else allowed_rs).append(float(c["blended_r"]))
    st_b = stats_for(blocked_rs)
    st_a = stats_for(allowed_rs)
    missed = sum(1 for r in blocked_rs if r > 0)
    avoided = sum(1 for r in blocked_rs if r <= 0)
    return {
        "name": "Lone-wolf paper overlay (hybrid+no-lonewolf)",
        "signals_seen": len(overlays),
        "signals_sector_mapped": mapped,
        "would_have_blocked": len(blocked_ids),
        "opened": "n/a (overlay never opens; baseline decides)",
        "open_now": None,
        "closed_trades": st_b["closed"] + st_a["closed"],
        "expectancy_r_blocked": st_b["expectancy_r"],
        "expectancy_r_allowed": st_a["expectancy_r"],
        "expectancy_r": st_a["expectancy_r"],  # the overlay's realized book = allowed only
        "win_rate": st_a["win_rate"],
        "profit_factor": st_a["profit_factor"],
        "worst_mae_r": None,
        "best_mfe_r": None,
        "mfe_mae_note": "inherits baseline close records; not duplicated",
        "missed_winners": missed if blocked_ids else "n/a (0 blocked so far)",
        "avoided_losers": avoided if blocked_ids else "n/a (0 blocked so far)",
        "sample_warning": size_warning(st_b["closed"] + st_a["closed"],
                                       "blocked+allowed closed trades")
        + " | mapped-universe only; most forward signals are unmapped",
    }


# ---------------------------------------------------------------- ADX shadow
def adx_board(fwd_signals, fwd_closes):
    """Shadow: on crowded bars (> SLOT_CAP signals at one bar close), what
    would ADX-descending top-SLOT_CAP selection have taken vs baseline?
    Returns (board, feasible_bool, note)."""
    # Feasibility: need per-signal adx + bar grouping + baseline admission.
    adx_ok = all(s.get("adx") is not None for s in fwd_signals.values())
    by_bar = defaultdict(list)
    for sid, s in fwd_signals.items():
        by_bar[s.get("signal_bar_close_at")].append(sid)
    crowded = {b: ids for b, ids in by_bar.items() if len(ids) > SLOT_CAP}
    if not adx_ok:
        return ({
            "name": "ADX ranking shadow",
            "feasible": False,
            "note": "not feasible yet — forward-test signal log is missing per-signal ADX on some signals",
        }, False)
    # Shadow selection: top SLOT_CAP by ADX desc on each crowded bar.
    shadow_selected, baseline_selected = set(), set()
    for bar, ids in crowded.items():
        ranked = sorted(ids, key=lambda i: fwd_signals[i].get("adx") or 0, reverse=True)
        shadow_selected.update(ranked[:SLOT_CAP])
    # Baseline admission: which signals opened (the harness's real choice).
    # Reconstruct from closes+opened is done by caller; here approximate via
    # signals that have a close record or were opened. We pass opened set in.
    return (crowded, shadow_selected, adx_ok)


def adx_board_full(fwd_signals, opened_ids, fwd_closes):
    crowded_info = adx_board(fwd_signals, fwd_closes)
    if isinstance(crowded_info[0], dict) and not crowded_info[0].get("feasible", True):
        return crowded_info[0]
    crowded, shadow_selected, _ = crowded_info
    by_bar = defaultdict(list)
    for sid, s in fwd_signals.items():
        by_bar[s.get("signal_bar_close_at")].append(sid)
    max_per_bar = max((len(v) for v in by_bar.values()), default=0)
    if not crowded:
        return {
            "name": "ADX ranking shadow",
            "feasible": True,
            "signals_seen": len(fwd_signals),
            "crowded_bars": 0,
            "note": f"ranking never bound — no bar exceeded the {SLOT_CAP}-slot cap "
                    f"(max seen: {max_per_bar}/bar); shadow selection is identical to baseline",
            "closed_trades": None,
            "expectancy_r": None,
            "win_rate": None,
            "profit_factor": None,
            "missed_winners": "n/a (ranking never bound)",
            "avoided_losers": "n/a (ranking never bound)",
            "sample_warning": "n=0 crowded bars — shadow is vacuous until a bar exceeds the slot cap",
        }
    # Crowded bars exist: compare shadow picks vs baseline picks on those bars.
    shadow_rs = [float(fwd_closes[s]["blended_r"]) for s in shadow_selected
                 if s in fwd_closes and fwd_closes[s].get("blended_r") is not None]
    base_rs = [float(fwd_closes[s]["blended_r"])
               for bar_ids in crowded.values() for s in bar_ids
               if s in opened_ids and s in fwd_closes
               and fwd_closes[s].get("blended_r") is not None]
    st = stats_for(shadow_rs)
    return {
        "name": "ADX ranking shadow",
        "feasible": True,
        "signals_seen": len(fwd_signals),
        "crowded_bars": len(crowded),
        "shadow_picks": len(shadow_selected),
        "closed_trades": st["closed"],
        "expectancy_r": st["expectancy_r"],
        "win_rate": st["win_rate"],
        "profit_factor": st["profit_factor"],
        "missed_winners": "see baseline comparison (shadow is a re-ranking, not a filter)",
        "avoided_losers": "see baseline comparison (shadow is a re-ranking, not a filter)",
        "sample_warning": size_warning(st["closed"], "shadow closed trades"),
    }


def render_text(boards):
    lines = []
    lines.append("=" * 72)
    lines.append("QUALITY FLOW FORWARD-TEST SCOREBOARD (read-only, paper sidecars)")
    lines.append("V5.4 frozen — nothing here changes production. Tiny live sample:")
    lines.append("do NOT declare a winner.")
    lines.append("=" * 72)
    for b in boards:
        lines.append("")
        lines.append(f"--- {b['name']} ---")
        if b.get("feasible") is False:
            lines.append(f"  status: {b.get('note')}")
            continue
        rows = [
            ("signals seen", b.get("signals_seen")),
            ("signals skipped", b.get("signals_skipped")),
            ("opened", b.get("opened")),
            ("open now", b.get("open_now")),
            ("closed trades", b.get("closed_trades")),
            ("expectancy (R)", fmt(b.get("expectancy_r"))),
            ("win rate", fmt(b.get("win_rate")) if b.get("win_rate") is None else f"{b['win_rate']:.1%}"),
            ("profit factor", fmt(b.get("profit_factor"))),
            ("worst MAE (R)", fmt(b.get("worst_mae_r"))),
            ("best MFE (R)", fmt(b.get("best_mfe_r"))),
            ("MFE/MAE source", b.get("mfe_mae_note")),
            ("missed winners", b.get("missed_winners")),
            ("avoided losers", b.get("avoided_losers")),
        ]
        if "would_have_blocked" in b:
            rows.insert(2, ("would-have-blocked", b["would_have_blocked"]))
            rows.insert(3, ("sector-mapped signals", b.get("signals_sector_mapped")))
            rows.append(("expectancy blocked (R)", fmt(b.get("expectancy_r_blocked"))))
            rows.append(("expectancy allowed (R)", fmt(b.get("expectancy_r_allowed"))))
        if "crowded_bars" in b:
            rows.append(("crowded bars", b.get("crowded_bars")))
        if b.get("note"):
            rows.append(("note", b["note"]))
        for k, v in rows:
            lines.append(f"  {k:26s} {'n/a' if v is None else v}")
        lines.append(f"  SAMPLE WARNING: {b.get('sample_warning')}")
    lines.append("")
    lines.append("=" * 72)
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Read-only forward-test scoreboard")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = ap.parse_args()

    base, fwd_signals, fwd_closes = baseline_board()
    # opened set for ADX shadow
    opened_ids = set()
    for r in read_jsonl(FWD_LOG):
        if r.get("type") == "event" and r.get("event") == "opened":
            opened_ids.add(r["signal_id"])
    fvg = fvg_board()
    lw = lonewolf_board(fwd_closes)
    adx = adx_board_full(fwd_signals, opened_ids, fwd_closes)

    boards = [base, fvg, lw, adx]
    if args.json:
        print(json.dumps({"boards": boards}, indent=1, default=str))
    else:
        print(render_text(boards))


if __name__ == "__main__":
    main()
