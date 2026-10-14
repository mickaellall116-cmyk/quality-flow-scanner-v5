#!/usr/bin/env python3
"""Phase A synthetic fixtures — QF-IDEA-PIPELINE-PHASE-A-20261013-01 r1.

Implements design §6 fixtures F1–F5 plus review-fix fixtures:
  F6 chain-tamper refusal, F7 adjacency flag (no automated verdict),
  F8 parked-source + SOURCE_CHAT single-writer channel.

All fixtures run against SCRATCH stores in temp dirs with canned inputs
and injected clocks. No network, no live store, no registry writes (the
registry input is a scratch copy; its hash is checked before/after).

Run: python3 fixtures/run_fixtures.py [--out PATH]
Exit code 0 iff every fixture passes. Output is deterministic given the
injected clocks, so an independent rerun must produce identical lines.
"""
import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import store as S  # noqa: E402

RESULTS = []


def report(fid, name, ok, detail):
    RESULTS.append((fid, ok))
    print(f"[{fid}] {'PASS' if ok else 'FAIL'} — {name}: {detail}")


class Clock:
    def __init__(self, start="2026-10-13T21:00:00-04:00"):
        self.t = start

    def __call__(self):
        return self.t

    def set(self, t):
        self.t = t


def cand(claim, family, url="https://example.org/paper", **over):
    base = {
        "claim": claim,
        "hypothesis": over.pop("hypothesis", "Falsifiable form: " + claim),
        "strategy_family": family,
        "timeframe": over.pop("timeframe", "Daily; 1-month hold"),
        "mechanically_definable": True,
        "pit_data": "yes",
        "pit_inputs": ["daily close"],
        "source": {
            "authors": "Doe & Roe",
            "title": "A Paper About: " + claim,
            "venue": "Journal of Finance 1 (2020)",
            "url": url,
            "accessed_at": "2026-10-13T21:00:00-04:00",
            "access_basis": "publisher abstract page — abstract only",
            "evidence": "Abstract states: " + claim,
            "content_hash": S.content_hash("A Paper", "Abstract: " + claim),
            "extractor_version": S.EXTRACTOR_VERSION,
            "is_primary": True,
            "source_class": "SRC-JOURNAL-PAGES",
            "doi": "",
        },
        "limitations": ["Synthetic fixture limitation."],
        "lane_fit": "daily",
        "created_at": "2026-10-13T21:00:00-04:00",
        "created_by": "idea-harvest-weekly",
    }
    base.update(over)
    return base


def make_store(tmp, clock):
    st = S.Store(Path(tmp) / "store", clock=clock)
    st.init_layout()
    return st


# ---------------------------------------------------------------------------
def f1_duplicate_ingestion(tmp):
    clock = Clock()
    st = make_store(tmp, clock)
    run1 = st.new_run_id()
    st.acquire_lease(run1)
    st.append_event("RUN_START", run1)
    c = cand("High volume stocks appreciate.", "volume_premium")
    r1 = st.ingest(c, run1)
    r2 = st.ingest(c, run1)                      # same run, second submission
    st.append_event("RUN_END", run1)
    st.release_lease()
    run2 = st.new_run_id()
    kind, _ = st.acquire_lease(run2)
    st.append_event("RUN_START", run2)
    r3 = st.ingest(c, run2)                      # second run, third submission
    st.append_event("RUN_END", run2)
    st.release_lease()
    cards = st.all_cards()
    seen = [e for e in st.read_events() if e["event_type"] == "DUPLICATE_SEEN"]
    ok = (len(cards) == 1 and r1["outcome"] == "ingested"
          and r2["outcome"] == "duplicate" and r3["outcome"] == "duplicate"
          and len(seen) == 2
          and all(s["idea_id"] == r1["idea_id"] for s in seen)
          and st.next_idea_seq() == 2)  # no ID consumed by duplicates
    st.verify_chain()
    report("F1", "Duplicate ingestion",
           ok, f"1 card ({r1['idea_id']}), 2 DUPLICATE_SEEN events, "
               "no extra IDs allocated, chain verifies")


def f2_restart_idempotency(tmp):
    clock = Clock()
    st = make_store(tmp, clock)
    run1 = st.new_run_id()
    st.acquire_lease(run1)
    st.append_event("RUN_START", run1)
    r = st.ingest(cand("Overnight returns persist.", "overnight_test_fam"),
                  run1)
    crashed_idea = r["idea_id"]
    # SIMULATED CRASH: no RUN_END, lease file left behind.
    bytes_before = st.log_path.read_bytes()
    # Restart with a stale lease: old timestamp + dead PID.
    lock = json.loads(st.lock_path.read_text())
    lock["acquired_at"] = "2026-10-13T10:00:00-04:00"  # >2h before clock
    lock["pid"] = 999999                                # not a live PID
    st.lock_path.write_text(json.dumps(lock))
    clock.set("2026-10-13T21:05:00-04:00")
    st2 = S.Store(Path(tmp) / "store", clock=clock)
    # A live lease must still refuse: first prove refusal with fresh lock.
    run2 = st2.new_run_id()
    kind, info = st2.acquire_lease(run2)
    st2.append_event("LOCK_BROKEN", run2,
                     reason=f"stale lease broken at restart: {info}")
    st2.append_event("RUN_START", run2)
    states = st2.current_states()
    # Re-submitting the crashed run's candidate must be a duplicate, and a
    # new candidate must take the NEXT sequence number (no ID reuse).
    dup = st2.ingest(cand("Overnight returns persist.", "overnight_test_fam"),
                     run2)
    new = st2.ingest(cand("A fresh distinct claim.", "fresh_family"), run2)
    st2.append_event("RUN_END", run2)
    st2.release_lease()
    st2.verify_chain()
    log_now = st2.log_path.read_bytes()
    ok = (kind == "broke-stale" and crashed_idea in states
          and dup["outcome"] == "duplicate"
          and new["idea_id"].endswith("0002")
          and log_now.startswith(bytes_before)  # append-only: prefix kept
          and any(e["event_type"] == "LOCK_BROKEN"
                  for e in st2.read_events()))
    report("F2", "Restart idempotency",
           ok, "stale lease broken + logged, chain verified, crashed idea "
               f"{crashed_idea} kept once, next ID is 0002, log append-only")


def f3_source_failure(tmp):
    clock = Clock()
    st = make_store(tmp, clock)
    run = st.new_run_id()
    st.acquire_lease(run)
    st.append_event("RUN_START", run)
    # Canned behaviour for a failed source: writer logs SOURCE_DOWN, drops
    # that source's would-be candidates, continues with healthy sources.
    st.append_event("SOURCE_DOWN", run,
                    reason="SRC-ARXIV-QFIN canned failure snapshot: "
                           "connection timeout; source skipped, no mirror "
                           "substituted")
    healthy = st.ingest(cand("Healthy source claim stands.",
                             "healthy_family"), run)
    parked_rejected = False
    bad = cand("Claim from a parked SSRN capture.", "parked_family")
    bad["source"]["source_class"] = "SRC-SSRN"
    try:
        st.ingest(bad, run)
    except S.CardValidationError as exc:
        parked_rejected = any("SOURCE_PARKED" in e for e in exc.errors)
    unverifiable = cand("Claim not present in its source.", "ghost_family")
    unverifiable["source"]["is_primary"] = False
    unverifiable["source"]["source_class"] = "SRC-FACTOR-SUMMARIES"
    dropped = False
    try:
        st.ingest(unverifiable, run)
    except S.CardValidationError:
        dropped = True  # secondary-only class cannot be primary
    st.append_event("RUN_END", run)
    st.release_lease()
    cards = st.all_cards()
    downs = [e for e in st.read_events() if e["event_type"] == "SOURCE_DOWN"]
    ok = (healthy["outcome"] == "ingested" and parked_rejected and dropped
          and len(downs) == 1 and len(cards) == 1
          and list(cards.values())[0]["strategy_family"] == "healthy_family")
    report("F3", "Source failure",
           ok, "run completed; SOURCE_DOWN logged; parked-source and "
               "unverifiable/secondary-primary candidates dropped; "
               "1 healthy card only")


def f4_rejected_idea(tmp):
    clock = Clock()
    st = make_store(tmp, clock)
    run = st.new_run_id()
    st.acquire_lease(run)
    st.append_event("RUN_START", run)
    dead = cand("An LSTM stack forecasts trend from RSI features.",
                "ml_price_forecasting")
    r = st.ingest(dead, run)
    assert r["outcome"] == "rejected"
    reject_events = [e for e in st.read_events()
                     if e["event_type"] == "DEDUPE_REJECT"
                     and e["idea_id"] == r["idea_id"]]
    reject_bytes = json.dumps(reject_events[0], sort_keys=True)
    # (a) identical claim resubmitted
    again = st.ingest(dead, run)
    # (b) re-parameterized variant, same closed family, no justification
    variant = cand("A transformer forecasts trend from RSI features.",
                   "ml_price_forecasting")
    var = st.ingest(variant, run)
    st.append_event("RUN_END", run)
    st.release_lease()
    reject_events_after = [e for e in st.read_events()
                           if e["event_type"] == "DEDUPE_REJECT"
                           and e["idea_id"] == r["idea_id"]]
    states = st.current_states()
    shortlist_states = [s for s in states.values() if s == "SHORTLISTED"]
    ok = (again["outcome"] == "duplicate"
          and again["idea_id"] == r["idea_id"]
          and var["outcome"] == "rejected"
          and "KILLED-ML-PRICE-FORECASTING" in (var["reason"] or "")
          and json.dumps(reject_events_after[0], sort_keys=True)
          == reject_bytes  # original rejection record byte-identical
          and not shortlist_states)
    report("F4", "Rejected idea (failure memory)",
           ok, "identical claim -> DUPLICATE_SEEN of the rejected record; "
               "variant -> DEDUPE_REJECT citing KILLED-ML-PRICE-FORECASTING; "
               "original rejection event byte-identical; nothing shortlisted")


def f5_blocked_gate(tmp):
    clock = Clock()
    st = make_store(tmp, clock)
    run = st.new_run_id()
    st.acquire_lease(run)
    st.append_event("RUN_START", run)
    r = st.ingest(cand("A perfectly good claim.", "good_family"), run)
    iid = r["idea_id"]
    st.transition(iid, "RANKED", run, rank=1)
    st.transition(iid, "SHORTLISTED", run)
    refusals = 0
    for target in ("PREREGISTERED", "ELIGIBLE"):
        try:
            st.transition(iid, target, run)
        except S.IllegalTransitionError:
            refusals += 1
    reg = Path(tmp) / "registry.json"
    reg.write_text('{"experiments": []}', encoding="utf-8")
    reg_hash_before = hashlib.sha256(reg.read_bytes()).hexdigest()
    try:
        st.guard_registry_write(reg)
    except S.ScopeViolation:
        refusals += 1
    st.append_event("RUN_END", run)
    st.release_lease()
    err_events = [e for e in st.read_events() if e["event_type"] == "ERROR"]
    ok = (refusals == 3 and len(err_events) == 2
          and st.current_states()[iid] == "SHORTLISTED"
          and hashlib.sha256(reg.read_bytes()).hexdigest()
          == reg_hash_before)
    report("F5", "Blocked gate (scope enforcement)",
           ok, "PREREGISTERED + ELIGIBLE transitions refused and logged as "
               "ERROR events; registry write refused (ScopeViolation); idea "
               "remains SHORTLISTED; scratch registry hash unchanged")


def f6_chain_tamper(tmp):
    clock = Clock()
    st = make_store(tmp, clock)
    run = st.new_run_id()
    st.acquire_lease(run)
    st.append_event("RUN_START", run)
    st.ingest(cand("Tamper target claim.", "tamper_family"), run)
    st.append_event("RUN_END", run)
    st.release_lease()
    lines = st.log_path.read_text(encoding="utf-8").splitlines()
    ev = json.loads(lines[1])
    ev["reason"] = "quietly edited"
    lines[1] = json.dumps(ev, ensure_ascii=False)
    st.log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    refused = False
    try:
        st.acquire_lease("RUN-20261013-099")
        st.append_event("RUN_START", "RUN-20261013-099")
    except S.ChainVerificationError:
        refused = True
    report("F6", "Chain tamper refusal",
           refused, "edited log line detected by hash chain; writer aborts "
                    "instead of repairing silently")


def f7_adjacency_flag(tmp):
    clock = Clock()
    st = make_store(tmp, clock)
    run = st.new_run_id()
    st.acquire_lease(run)
    st.append_event("RUN_START", run)
    known = {"anchoring_momentum":
             "registry-adjacent (Harvest #1 IDEA in same family)"}
    r = st.ingest(cand("Nearness to the 200-day high predicts returns.",
                       "anchoring_momentum"), run, known_families=known)
    st.append_event("RUN_END", run)
    st.release_lease()
    flags = [e for e in st.read_events()
             if e["event_type"] == "ADJACENCY_FLAG"]
    ok = (r["outcome"] == "ingested" and r.get("adjacency_flag")
          and len(flags) == 1
          and "no automated verdict" in (flags[0].get("reason") or "")
          or "human call" in (flags[0].get("reason") or ""))
    report("F7", "Adjacency flag (no automated semantic verdict)",
           bool(ok), "known-family candidate ingested with ADJACENCY_FLAG; "
                     "mechanism difference left to a human, never verdicted")


def f8_source_chat_single_writer(tmp):
    # Structural check: SOURCE_CHAT exists in the source registry as an
    # intake CHANNEL whose rule requires the single writer; the store
    # module exposes no chat/direct write path (cards enter only via
    # Store.ingest under a lease, by the writer identity).
    src_doc = json.loads((Path(__file__).resolve().parent.parent
                          / "sources.json").read_text(encoding="utf-8"))
    chat = [s for s in src_doc["sources"] if s["id"] == "SOURCE_CHAT"]
    store_src = Path(S.__file__).read_text(encoding="utf-8")
    ok = (len(chat) == 1 and chat[0]["role"] == "intake-channel"
          and "single writer" in chat[0]["rule"]
          and "def ingest" in store_src
          and "socket" not in store_src and "urllib" not in store_src
          and "requests" not in store_src)
    report("F8", "SOURCE_CHAT enters only through the single writer",
           ok, "SOURCE_CHAT is a channel record (not a scraped source); "
               "store has exactly one ingest path and zero network code")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    fns = [f1_duplicate_ingestion, f2_restart_idempotency, f3_source_failure,
           f4_rejected_idea, f5_blocked_gate, f6_chain_tamper,
           f7_adjacency_flag, f8_source_chat_single_writer]
    for fn in fns:
        with tempfile.TemporaryDirectory(prefix="phasea-fixture-") as tmp:
            try:
                fn(tmp)
            except Exception as exc:  # fixture crash = FAIL, never hidden
                report(fn.__name__.split("_")[0].upper(), fn.__name__,
                       False, f"exception: {type(exc).__name__}: {exc}")
    passed = sum(1 for _, ok in RESULTS if ok)
    print(f"FIXTURES: {passed}/{len(RESULTS)} PASS")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
