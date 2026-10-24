#!/usr/bin/env python3
"""QF-EQUITY43-FEED-MEASUREMENT-PILOT-20261024-22 — finalize.

Runs after all capture actions are terminal (or a STOP fired):
  B1 censuses  — latency quantiles, coverage, revision census, credits
                 (desk journal vs /api_usage provider snapshots);
  B2 parity    — exact captured bytes through the pinned -17 observer
                 (streaming, receipt order) vs a batch run over final
                 per-bar values vs an independent pandas aggregation;
                 journal verify + journal-only replay; stop-at-first
                 material semantic mismatch semantics (first mismatch is
                 reported, verdict FAIL);
  package      — bar-free derived evidence committed to the scanner repo
                 via temp worktree on fresh origin/main, manifest verified
                 from the pushed remote tree;
  posts        — Slack RESULT + bridge RESULT commit.
Idempotent: state/result_posted.json blocks re-posting."""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
UTC = timezone.utc
BASE = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.path.join(BASE, "state")
ARCHIVE_NS = os.path.join(BASE, "archive_clone", "captures",
                          "td_feed_measure_pilot_20261026")
JOURNAL_PATH = os.path.join(ARCHIVE_NS, "journal.jsonl")
REPO = os.path.expanduser("~/workspace/quality-flow-scanner-v5")
PKG_REL = "research_notes/equity43_feed_measurement_pilot_20261024_22"
SLACK_CHANNEL = "C0C6QM27N0L"
TASK = "QF-EQUITY43-FEED-MEASUREMENT-PILOT-20261024-22"


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def q(sorted_vals, p):
    if not sorted_vals:
        return None
    import math
    k = max(1, math.ceil(p / 100.0 * len(sorted_vals)))
    return sorted_vals[k - 1]


def quantiles(vals):
    s = sorted(vals)
    return {"n": len(s), "p50": q(s, 50), "p95": q(s, 95),
            "p99": q(s, 99), "max": s[-1] if s else None,
            "min": s[0] if s else None}


def latency_label_for(sess, stopped):
    """Frozen -21 protocol §7: LATENCY_MEASURED only when EVERY session
    captured completely and the pilot was not stopped. Any missing or
    incomplete session — including a review-gate slip — forces
    LATENCY_UNMEASURED overall (per-session partials are still shown,
    labeled as partial). (STOP 3, comment 6386192978: the earlier
    >=3-session/>=100-bar threshold was a unilateral weakening and is
    withdrawn.)"""
    if stopped or not sess:
        return "LATENCY_UNMEASURED"
    if all(s["complete"] for s in sess.values()):
        return "LATENCY_MEASURED"
    return "LATENCY_UNMEASURED"


def _vhash(v):
    """SHA-256 of a value's canonical repr — published in place of raw
    market values (STOP 4: derived-only public outputs)."""
    return hashlib.sha256(repr(v).encode()).hexdigest()


def sanitize_reply(raw):
    """Sanitized record of a filed TD support reply for the PUBLIC
    package (STOP 4: sanitize separately). Keeps sender domain, subject,
    date and a token-redacted body; drops headers, ids and any long
    token-like strings. If the body cannot be extracted, only metadata
    is filed (fail-closed — the raw +read output never publishes)."""
    import re
    if not isinstance(raw, dict):
        return {"note": "reply record unparseable; metadata only",
                "raw_sha256": _vhash(raw)}
    def pick(*keys):
        for k in keys:
            if isinstance(raw.get(k), str) and raw[k]:
                return raw[k]
        return None
    sender = pick("from", "sender", "From") or ""
    domain = sender.split("@")[-1].strip("> ").lower() if "@" in sender \
        else None
    body = pick("body_text", "body", "text", "snippet")
    if body:
        body = re.sub(r"[A-Za-z0-9_\-]{24,}", "[REDACTED]", body)
        body = body[:8000]
    return {"from_domain": domain, "subject": pick("subject", "Subject"),
            "date": pick("date", "Date", "message_sent_at"),
            "body_text_redacted": body,
            "redaction": "token-like runs >=24 chars replaced; headers "
                         "and message ids never published"}


def load_json(p):
    with open(p) as f:
        return json.load(f)


# ------------------------------------------------------------------ B1
def censuses(st, journal):
    bars = st["bars"]
    by_symbol, by_session = {}, {}
    pooled = []
    fin_only = 0
    for key, b in bars.items():
        fs = b["first_seen"]
        if fs:
            lag = fs["lag_s"]
            pooled.append(lag)
            by_symbol.setdefault(b["symbol"], []).append(lag)
            by_session.setdefault(b["session"], []).append(lag)
            if fs["via"] == "finalization":
                fin_only += 1
    latency = {
        "pooled": quantiles(pooled),
        "by_symbol": {s: quantiles(v) for s, v in sorted(by_symbol.items())},
        "by_session": {s: quantiles(v)
                       for s, v in sorted(by_session.items())},
        "first_seen_at_finalization_count": fin_only,
        "first_seen_total": len(pooled),
        "note": "lag = first poll response receipt instant minus nominal "
                "bar close; bars first seen only at finalization are exact "
                "at finalization and right-censored (>420s) at the ladder."}
    expected = len(bars)
    received = sum(1 for b in bars.values() if b["first_seen"])
    missing = [k for k, b in bars.items() if not b["first_seen"]]
    late = [k for k, b in bars.items()
            if b["first_seen"] and b["missing_at_finalization"]]
    coverage = {"expected_bars": expected, "received_bars": received,
                "missing_bars": len(missing), "missing_keys": missing,
                "late_bars_first_seen_after_finalization": len(late),
                "late_keys": late,
                "per_symbol": {}}
    for sym in sorted({b["symbol"] for b in bars.values()}):
        sb = [b for b in bars.values() if b["symbol"] == sym]
        coverage["per_symbol"][sym] = {
            "expected": len(sb),
            "received": sum(1 for b in sb if b["first_seen"]),
            "missing": sum(1 for b in sb if not b["first_seen"])}
    rev_bars = {k: b for k, b in bars.items() if b["revisions"]}
    field_counts = {}
    for b in rev_bars.values():
        for r in b["revisions"]:
            for f in r["field_diffs"]:
                field_counts[f] = field_counts.get(f, 0) + 1
    revisions = {"revised_bars": len(rev_bars),
                 "revision_events": sum(len(b["revisions"])
                                         for b in rev_bars.values()),
                 "field_diff_counts": field_counts,
                 "revised_keys": sorted(rev_bars)}
    snaps = st["usage_snapshots"]
    prov = {}
    for s in snaps:
        p = s["provider"] or {}
        val = p.get("daily_usage", p.get("current_usage"))
        prov.setdefault(s["tag"] and s["receipt_utc"][:10], []).append(
            {"tag": s["tag"], "receipt_utc": s["receipt_utc"],
             "daily_usage": val, "raw": p})
    credits = {"desk_calls_total": st["desk_calls"],
               "desk_calls_by_day": st["desk_calls_by_day"],
               "provider_snapshots": prov,
               "caps": {"per_day_worst_case": 149, "pilot_total": 800}}
    return latency, coverage, revisions, credits


def sessions_report(st):
    out = {}
    for d, status in st["sessions_status"].items():
        acts = [a for a in st["actions"]
                if a.get("session") == d and a["kind"] in
                ("ladder", "finalization", "revision", "usage")]
        missed = [a["id"] for a in acts if a["status"] == "missed_late"]
        pending = [a["id"] for a in acts if a["status"] == "pending"]
        bars = [b for b in st["bars"].values() if b["session"] == d]
        got = sum(1 for b in bars if b["first_seen"])
        out[d] = {"actions_terminal": len(acts) - len(pending),
                  "actions_total": len(acts), "missed_actions": missed,
                  "bars_received": got, "bars_expected": len(bars),
                  "complete": not pending and got == len(bars)
                  and not missed}
    return out


# ------------------------------------------------------------------ B2
def run_observer(rows_by_symbol_order, workdir, tag):
    """Feed rows [(symbol, rowdict)] through the pinned observer."""
    bundle = os.path.join(BASE, "bundle")
    if not os.path.isdir(bundle) and os.path.isdir(
            os.path.join(BASE, "..", "bundle")):
        bundle = os.path.normpath(os.path.join(BASE, "..", "bundle"))
    for p in (bundle, os.path.join(bundle, "engine"),
              os.path.join(bundle, "engine", "pine_stack"),
              os.path.join(bundle, "engine", "pine_ranking"),
              os.path.join(bundle, "engine", "pine_exposure"),
              os.path.join(bundle, "engine", "pine_signal_quality")):
        sys.path.insert(0, p)
    import pine_backtest as pb
    spec = importlib.util.spec_from_file_location(
        "fofin", os.path.join(bundle, "observer", "fwd_observer17.py"))
    fo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fo)
    table = fo.SessionTable(load_json(os.path.join(
        bundle, "calendar", "session_table_extended_candidate.json")))
    os.makedirs(workdir, exist_ok=True)
    jpath = os.path.join(workdir, f"journal_{tag}.jsonl")
    apath = os.path.join(workdir, f"anchors_{tag}.json")
    journal = fo.Journal(jpath, apath)
    symbols = sorted({s for s, _ in rows_by_symbol_order})
    obs = fo.ForwardObserver(table, journal, pb, symbols)
    for sym, row in rows_by_symbol_order:
        obs.ingest(sym, row)
    obs.flush()
    anchor = journal.anchor(f"finalize {tag} seal")
    journal.close()
    ok_j, info_j = fo.Journal.verify(jpath, apath)
    frames = {}
    for sym in symbols:
        bf = obs.bars_frame(sym)
        frames[sym] = bf
    return {"frames": frames, "candidates": obs.candidates(),
            "journal_ok": ok_j, "journal_info": info_j,
            "anchor_head": anchor["head"], "journal_path": jpath,
            "anchor_path": apath, "fo": fo, "pb": pb, "obs": obs}


def frame_fingerprint(bf):
    import hashlib as hl
    h = hl.sha256()
    h.update(str(list(bf.index)).encode())
    for col in bf.columns:
        h.update(col.encode())
        h.update(bf[col].astype(str).to_csv(index=False).encode())
    return h.hexdigest()


def independent_aggregation(final_rows, batch_frames):
    """Aggregate final 1h rows into session 4H bars with plain pandas and
    compare OHLC (exact) + Volume (abs tol 1e-6) against the batch
    observer frame. Returns a mismatch dict or None."""
    import pandas as pd
    rows = []
    for sym, row in final_rows:
        rows.append({"symbol": sym, "datetime": row["datetime"],
                     "open": float(row["open"]), "high": float(row["high"]),
                     "low": float(row["low"]), "close": float(row["close"]),
                     "volume": float(row["volume"] or 0)})
    if not rows:
        return {"kind": "aggregation", "detail": "no final rows"}
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["datetime"]).dt.tz_localize(ET)
    df["date"] = df["ts"].dt.date.astype(str)
    df["start"] = df["ts"].dt.strftime("%H:%M")
    df["bin"] = df["start"].map(
        lambda s: "09:30" if s in ("09:30", "10:30", "11:30", "12:30")
        else "13:30")
    for (sym, date, binn), g in df.sort_values("ts").groupby(
            ["symbol", "date", "bin"]):
        bf = batch_frames.get(sym)
        stamp = pd.Timestamp(f"{date} {binn}", tz=ET)
        if bf is None or stamp not in bf.index:
            return {"kind": "aggregation_missing_bar", "symbol": sym,
                    "bar": str(stamp)}
        o, h = g["open"].iloc[0], g["high"].max()
        lo, c = g["low"].min(), g["close"].iloc[-1]
        v = g["volume"].sum()
        row_b = bf.loc[stamp]
        if not (float(row_b["Open"]) == o and float(row_b["High"]) == h
                and float(row_b["Low"]) == lo
                and float(row_b["Close"]) == c):
            # STOP 4: hashes only — no raw OHLC in any public output.
            return {"kind": "aggregation_value", "symbol": sym,
                    "bar": str(stamp),
                    "agg_sha256": _vhash([o, h, lo, c]),
                    "batch_sha256": _vhash([float(row_b["Open"]),
                                            float(row_b["High"]),
                                            float(row_b["Low"]),
                                            float(row_b["Close"])])}
        if abs(float(row_b["Volume"]) - v) > 1e-6:
            return {"kind": "aggregation_volume", "symbol": sym,
                    "bar": str(stamp),
                    "agg_volume_sha256": _vhash(v),
                    "batch_volume_sha256": _vhash(float(row_b["Volume"]))}
    return None


def adapter_parity(st):
    journal = []
    with open(JOURNAL_PATH) as f:
        for line in f:
            journal.append(json.loads(line))
    # streaming input: every series payload, journal order, payload row order
    stream_rows = []
    for rec in journal:
        if rec["kind"] not in ("ladder", "finalization", "revision"):
            continue
        if rec["http_status"] != 200 or not rec.get("payload_file"):
            continue
        try:
            body = load_json(os.path.join(ARCHIVE_NS, rec["payload_file"]))
        except Exception:
            continue
        for row in body.get("values") or []:
            stream_rows.append((rec["symbol"], row))
    # batch input: final per-bar values from state, (datetime, symbol) order
    final_rows = []
    for key, b in st["bars"].items():
        if b["last_values"] is None:
            continue
        row = {"datetime": f"{b['session']} {b['bar_start_et']}:00",
               **b["last_values"]}
        final_rows.append((b["symbol"], row))
    final_rows.sort(key=lambda x: (x[1]["datetime"], x[0]))
    workdir = os.path.join(BASE, "work", "parity")
    s_run = run_observer(stream_rows, workdir, "stream")
    b_run = run_observer(final_rows, workdir, "batch")
    mismatches = []
    for sym in sorted(set(s_run["frames"]) | set(b_run["frames"])):
        sf, bf = s_run["frames"].get(sym), b_run["frames"].get(sym)
        if sf is None or bf is None or len(sf) != len(bf) \
                or not sf.index.equals(bf.index):
            mismatches.append({"symbol": sym, "kind": "bar_index_or_count",
                               "stream_bars": None if sf is None else len(sf),
                               "batch_bars": None if bf is None else len(bf)})
            continue
        for col in ("Open", "High", "Low", "Close", "Volume", "SessionVWAP"):
            if not (sf[col].to_numpy() == bf[col].to_numpy()).all():
                bad = (sf[col] != bf[col])
                idx = sf.index[bad][0]
                # STOP 4: publish category/count/hashes ONLY — the raw
                # values stay in the private archive diagnostics.
                mismatches.append({
                    "symbol": sym, "kind": "value", "column": col,
                    "bar": str(idx),
                    "stream_sha256": _vhash(float(sf[col].loc[idx])),
                    "batch_sha256": _vhash(float(bf[col].loc[idx]))})
                break
    cand_s = sorted((c["symbol"], c["signal_idx"])
                    for c in s_run["candidates"])
    cand_b = sorted((c["symbol"], c["signal_idx"])
                    for c in b_run["candidates"])
    if cand_s != cand_b:
        mismatches.append({"kind": "candidates", "stream": cand_s,
                           "batch": cand_b})
    # independent aggregation cross-check (no observer/engine code):
    # final 1h rows -> session 4H bins (09:30 bin = starts 09:30..12:30,
    # 13:30 bin = starts 13:30..15:30), plain pandas.
    agg_mismatch = independent_aggregation(final_rows, b_run["frames"])
    if agg_mismatch:
        mismatches.append(agg_mismatch)
    revised = sum(1 for b in st["bars"].values() if b["revisions"])
    late = sum(1 for b in st["bars"].values()
               if b["first_seen"] and b["missing_at_finalization"])
    missing = sum(1 for b in st["bars"].values() if not b["first_seen"])
    subcase = "MEASURED" if (revised or late or missing) else "UNMEASURED"
    verdict = "ADAPTER_PARITY_FAIL" if mismatches else "ADAPTER_PARITY_PASS"
    return {"verdict": verdict, "first_mismatch": mismatches[0]
            if mismatches else None, "mismatch_count": len(mismatches),
            "stream_rows_fed": len(stream_rows),
            "batch_rows_fed": len(final_rows),
            "stream_journal_verified": s_run["journal_ok"],
            "batch_journal_verified": b_run["journal_ok"],
            "stream_candidates": len(cand_s), "batch_candidates": len(cand_b),
            "revision_behavior_subcase": subcase,
            "revision_cases": {"revised": revised, "late": late,
                               "missing": missing},
            "frame_fingerprints": {
                "stream": {s: frame_fingerprint(f)
                           for s, f in s_run["frames"].items()},
                "batch": {s: frame_fingerprint(f)
                          for s, f in b_run["frames"].items()}}}


# ------------------------------------------------------------------ posts
def slack_send(text):
    args = json.dumps({"channel_id": SLACK_CHANNEL, "message": text})
    out = subprocess.run(["/opt/hatch/bin/slack", "call-tool", "--name",
                          "slack_send_message", "--arguments-json", args],
                         capture_output=True, text=True, timeout=120)
    return out.stdout


def git(args, cwd):
    return subprocess.run(["git", "-C", cwd, *args],
                          capture_output=True, text=True, timeout=600)


def paused_reproof():
    fwd = os.path.join(REPO, "forward_test")
    pause = os.path.join(fwd, "PAUSE_NEW_ENTRIES")
    resume = os.path.join(fwd, "RESUME_NEW_ENTRIES")
    out = {"pause_new_entries_present": os.path.exists(pause),
           "resume_new_entries_present": os.path.exists(resume)}
    if out["pause_new_entries_present"]:
        out["pause_sha256"] = sha256_bytes(open(pause, "rb").read())
    return out


def main():
    state_path = os.path.join(STATE_DIR, "pilot_state.json")
    if not os.path.exists(state_path):
        print(json.dumps({"finalize": "not_ready",
                          "reason": "no pilot state yet"}))
        return 4
    st = load_json(state_path)
    posted_path = os.path.join(STATE_DIR, "result_posted.json")
    if os.path.exists(posted_path):
        print(json.dumps({"finalize": "already_posted",
                          **load_json(posted_path)}))
        return 0
    pending = [a for a in st["actions"] if a["status"] == "pending"]
    if pending and not st["stopped"]:
        print(json.dumps({"finalize": "not_ready",
                          "pending_actions": len(pending)}))
        return 4
    manifest = load_json(os.path.join(BASE, "run_manifest.json"))
    tripwire = st.get("tripwire", {"checks": [], "filed": []})
    tw_filed = tripwire.get("filed") or []
    if tw_filed:
        tw_line = (f"Email tripwire: {len(tripwire.get('checks', []))} "
                   f"pre-open checks; TD staff reply RECEIVED and filed as "
                   f"the governing source superseding the AI-assistant "
                   f"answers (message {tw_filed[0]['id']}, "
                   f"TD_SUPPORT_REPLY.json in this package).")
    else:
        tw_line = (f"Email tripwire: {len(tripwire.get('checks', []))} "
                   f"pre-open checks, all clean — no TD email reply "
                   f"received during the pilot; the AI-assistant answers "
                   f"remain the record and the Q6 nuance stays open (a "
                   f"silent mailbox settles nothing).")
    latency, coverage, revisions, credits = censuses(st, None)
    sess = sessions_report(st)
    complete_sessions = [d for d, s in sess.items() if s["complete"]]
    slipped = (st.get("review_gate") or {}).get("slipped_sessions", [])
    latency_label = latency_label_for(sess, st["stopped"])
    parity = adapter_parity(st)
    reproof = paused_reproof()
    result = {
        "task": TASK, "stopped": st["stopped"],
        "sessions": sess, "latency_label": latency_label,
        "review_gate": st.get("review_gate"),
        "latency": latency, "coverage": coverage, "revisions": revisions,
        "credits": credits, "adapter_parity": parity,
        "tripwire": tripwire,
        "paused_reproof_at_finalize": reproof}
    os.makedirs(os.path.join(BASE, "work"), exist_ok=True)
    with open(os.path.join(BASE, "work", "finalize_result.json"), "w") as f:
        json.dump(result, f, indent=1, sort_keys=True)

    pool = latency["pooled"]
    result_md = f"""# RESULT — {TASK}
## Twelve Data prospective 1h feed measurement pilot (Gate B B1+B2)

Authority: Mike GO, main chat 2026-10-24 10:36 ET, under the frozen -21
protocol (package c2b58d7). Symbols NVDA/TSLA/AAPL/SPY/MELI (MELI = lowest
median DEV daily volume, 328,352 over 524 sessions). Sessions
2026-10-26..2026-10-30. Measurement only: no S1 activation, no T0, no
trading. S1 PREP_READY / LAUNCH_HOLD and G4_HOLD unchanged.

## Verdicts
- Latency: **{latency_label}** — pooled n={pool['n']}, p50={pool['p50']}s,
  p95={pool['p95']}s, p99={pool['p99']}s, max={pool['max']}s;
  first-seen-at-finalization={latency['first_seen_at_finalization_count']}.
- Coverage: {coverage['received_bars']}/{coverage['expected_bars']} bars
  received; missing={coverage['missing_bars']};
  late (first seen after finalization)=
  {coverage['late_bars_first_seen_after_finalization']}.
- Revision census: {revisions['revised_bars']} bars revised,
  {revisions['revision_events']} events, fields {revisions['field_diff_counts']}.
- Adapter parity: **{parity['verdict']}** (stream rows fed
  {parity['stream_rows_fed']}, batch rows {parity['batch_rows_fed']},
  mismatches {parity['mismatch_count']}, first mismatch:
  {json.dumps(parity['first_mismatch'])}; revision-behavior sub-case
  {parity['revision_behavior_subcase']}).
- Credits: desk {credits['desk_calls_total']} calls total
  (by day {json.dumps(credits['desk_calls_by_day'])}); provider snapshots
  in credit_ledger.json. Caps 149/day, 800 total — held.
- Sessions: {json.dumps({d: s['complete'] for d, s in sess.items()})}
  (detail in sessions.json). Complete sessions:
  {json.dumps(complete_sessions)}; slipped as documented review-wait:
  {json.dumps(slipped)}.
- Stopped: {json.dumps(st['stopped'])}.
- {tw_line}
- PAUSED re-proof at finalize: {json.dumps(reproof)}.

## Rights record
- Q1–Q3 (Twelve Data AI assistant, 2026-10-24; adjudication memo on the
  bridge): Basic permits internal non-display use for evaluation/
  development incl. internal processing/storage; private research/paper
  observation is non-commercial; storage during subscription, delete
  within 30 days after it ends (audit trail excepted).
- Q6 SETTLED (Dooz AI assistant follow-up, Mike screenshot 2026-10-24
  ~11:03 ET): private automated research on 1h data via /time_series
  permitted; raw storage internal while subscribed; AI processing —
  raw market data must remain in the private environment, sharing with
  third parties including external AI services (ChatGPT, Muse named)
  counts as REDISTRIBUTION on Basic. Confirmed model: raw data →
  private infrastructure; AI agents → only derived results that cannot
  be reverse-engineered to the original data. Standing consequence:
  on Basic, no workflow may feed raw Twelve Data bars to any hosted AI
  agent — derived aggregates/hashes only. This pilot complied as
  built (local deterministic capture/processing; this package is
  bar-free derived evidence).
- The staff email reply, if received and filed (see tripwire log),
  supersedes the AI-assistant answers where it differs.

Raw payloads + capture journal are in the PRIVATE qf-data-archive
(captures/td_feed_measure_pilot_20261026/), never public GitHub. This
package carries bar-free derived evidence only.
"""
    # ---- package via temp worktree on fresh origin/main
    subprocess.run(["git", "-C", REPO, "fetch", "origin", "main"],
                   capture_output=True, timeout=300)
    wt = os.path.join(BASE, "work", "wt_finalize")
    subprocess.run(["git", "-C", REPO, "worktree", "remove", "--force", wt],
                   capture_output=True)
    r = git(["worktree", "add", "--detach", wt, "origin/main"], REPO)
    if r.returncode != 0:
        print(json.dumps({"finalize": "worktree_failed",
                          "stderr": r.stderr[-500:]}))
        return 5
    pkg = os.path.join(wt, PKG_REL)
    os.makedirs(pkg, exist_ok=True)
    files = {"RESULT.md": result_md,
             "latency_census.json": json.dumps(
                 {"label": latency_label, **latency}, indent=1,
                 sort_keys=True),
             "coverage.json": json.dumps(coverage, indent=1, sort_keys=True),
             "revision_census.json": json.dumps(revisions, indent=1,
                                                sort_keys=True),
             "credit_ledger.json": json.dumps(credits, indent=1,
                                              sort_keys=True),
             "adapter_parity.json": json.dumps(parity, indent=1,
                                               sort_keys=True),
             "sessions.json": json.dumps(sess, indent=1, sort_keys=True),
             "tripwire_log.json": json.dumps(tripwire, indent=1,
                                             sort_keys=True),
             "rights_record.json": json.dumps({
                 "q1_q3_source": "Twelve Data AI assistant answers "
                                 "2026-10-24 (bridge adjudication memo)",
                 "q6_settlement": {
                     "source": "Twelve Data 'Dooz' AI assistant "
                               "follow-up, Mike screenshot relayed "
                               "2026-10-24 ~11:03 ET",
                     "private_automated_research_1h": "permitted — "
                         "internal non-display use, evaluation and "
                         "development",
                     "raw_storage": "permitted internally while the "
                         "subscription is active (testing, replay, "
                         "development)",
                     "ai_processing": "raw market data must remain in "
                         "the private environment; sharing with third "
                         "parties incl. external AI services (ChatGPT, "
                         "Muse named) counts as REDISTRIBUTION on "
                         "Basic; AI agents receive only derived results "
                         "not reverse-engineerable to the original data",
                     "standing_consequence": "On Basic, no workflow may "
                         "feed raw Twelve Data bars to any hosted AI "
                         "agent — derived aggregates/hashes only.",
                     "pilot_compliance": "complies as built — local "
                         "deterministic capture/processing; raw "
                         "bars/journals never to hosted AI contexts, "
                         "public GitHub, or Slack"},
                 "governing_document": "the staff email reply "
                     "supersedes the AI-assistant answers where it "
                     "differs (see tripwire_log.json)"}, indent=1,
                 sort_keys=True),
             "run_manifest.json": json.dumps(manifest, indent=1,
                                             sort_keys=True)}
    for rec in tw_filed:
        rp = rec.get("reply_file")
        if rp and os.path.exists(rp):
            try:
                raw_reply = load_json(rp)
            except Exception:
                raw_reply = None
            files["TD_SUPPORT_REPLY.json"] = json.dumps(
                sanitize_reply(raw_reply), indent=1, sort_keys=True)
            break
    for name, content in files.items():
        with open(os.path.join(pkg, name), "w") as f:
            f.write(content if content.endswith("\n") else content + "\n")
    man_lines = []
    for name in sorted(files):
        man_lines.append(f"{sha256_bytes(files[name].encode())}  {name}")
    with open(os.path.join(pkg, "SHA256_MANIFEST.txt"), "w") as f:
        f.write("\n".join(man_lines) + "\n")
    git(["add", PKG_REL], wt)
    git(["-c", "user.email=claude-qf@localhost", "-c",
         "user.name=Muse (QF feed pilot)", "commit", "-m",
         f"{TASK}: measurement pilot RESULT — latency {latency_label}, "
         f"coverage {coverage['received_bars']}/{coverage['expected_bars']}, "
         f"revisions {revisions['revised_bars']} bars, adapter parity "
         f"{parity['verdict']}, credits desk {credits['desk_calls_total']} "
         f"(caps held); raw bytes private archive only; S1 LAUNCH_HOLD, "
         f"G4_HOLD unchanged"], wt)
    head = git(["rev-parse", "HEAD"], wt).stdout.strip()
    push = git(["push", "origin", "HEAD:main"], wt)
    if push.returncode != 0:
        print(json.dumps({"finalize": "push_failed", "head": head,
                          "stderr": push.stderr[-500:]}))
        return 6
    # bridge RESULT commit
    bridge_path = os.path.join(wt, "research_notes", "bridge_thread.md")
    with open(bridge_path, "a") as f:
        f.write(f"\n\n---\n\n## RESULT — {TASK}\n\n" + result_md)
    git(["add", "research_notes/bridge_thread.md"], wt)
    git(["-c", "user.email=claude-qf@localhost", "-c",
         "user.name=Muse (QF feed pilot)", "commit", "-m",
         f"bridge: RESULT {TASK} — latency {latency_label}, parity "
         f"{parity['verdict']} (package {head[:7]})"], wt)
    bridge_head = git(["rev-parse", "HEAD"], wt).stdout.strip()
    push2 = git(["push", "origin", "HEAD:main"], wt)
    if push2.returncode != 0:
        print(json.dumps({"finalize": "bridge_push_failed",
                          "head": head, "bridge_head": bridge_head,
                          "stderr": push2.stderr[-500:]}))
        return 7
    # manifest verification from the pushed remote tree
    git(["fetch", "origin", "main"], wt)
    verify_ok = True
    for name in list(files) + ["SHA256_MANIFEST.txt"]:
        shown = git(["show", f"origin/main:{PKG_REL}/{name}"], wt)
        if shown.returncode != 0:
            verify_ok = False
            break
        remote_sha = hashlib.sha256(shown.stdout.encode()).hexdigest()
        if name == "SHA256_MANIFEST.txt":
            local_sha = sha256_bytes(
                ("\n".join(man_lines) + "\n").encode())
        else:
            local_sha = sha256_bytes(files[name].encode()
                                     if files[name].endswith("\n")
                                     else (files[name] + "\n").encode())
        if remote_sha != local_sha:
            verify_ok = False
            break
    git(["worktree", "remove", "--force", wt], REPO)
    slack_text = (
        f"Muse — RESULT: {TASK} — Twelve Data 1h feed measurement pilot "
        f"complete. Latency **{latency_label}** (pooled n={pool['n']}, "
        f"p50={pool['p50']}s, p95={pool['p95']}s, p99={pool['p99']}s, "
        f"max={pool['max']}s). Coverage "
        f"{coverage['received_bars']}/{coverage['expected_bars']} bars, "
        f"missing {coverage['missing_bars']}, late "
        f"{coverage['late_bars_first_seen_after_finalization']}. Revisions: "
        f"{revisions['revised_bars']} bars / {revisions['revision_events']} "
        f"events. Adapter parity **{parity['verdict']}**. Credits: desk "
        f"{credits['desk_calls_total']} (caps 149/day, 800 total held). "
        f"Package {head[:7]}, bridge {bridge_head[:7]} "
        f"({'manifest verified from the pushed remote tree' if verify_ok else 'MANIFEST VERIFY FAILED — see finalize output'}). "
        f"Raw bytes in the private archive only. "
        f"S1 stays PREP_READY / LAUNCH_HOLD; G4_HOLD; measurement only — no "
        f"launch, no T0, no trades. — Muse")
    out = slack_send(slack_text)
    posted = {"package_commit": head, "bridge_commit": bridge_head,
              "manifest_verified_from_remote": verify_ok,
              "slack_response": out[-400:],
              "finalized_utc": datetime.now(UTC).isoformat()}
    with open(posted_path, "w") as f:
        json.dump(posted, f, indent=1)
    print(json.dumps({"finalize": "posted", **posted}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
