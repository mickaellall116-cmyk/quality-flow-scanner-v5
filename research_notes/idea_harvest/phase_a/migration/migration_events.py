#!/usr/bin/env python3
"""Harvest #1 migration + registry backfill — Phase A (schema/store only).

Builds, under migration/:
  - registry_backfill.json : derived family index over the PINNED registry
    blob (registry.json is read-only here; its sha256 is asserted unchanged
    before/after), with explicit coverage limits and family attributions.
  - store/                 : a Phase A store populated from the v1 artifacts
    (intake_draft_20261013.json + HARVEST_20261013.md) via MIGRATED events:
    6 shortlisted candidates + 2 dedupe-rejected candidates, with RANKED /
    SHORTLISTED / BLOCKED / DEDUPE_REJECT events replaying the v1 record,
    then deterministic drafts + family-ledger materializations.

Migration is DATA + EVENTS in the new store only. registry.json is never
written. No network. Refuses to overwrite an existing migration store.
"""
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
PHASE_A = HERE.parent
REPO = PHASE_A.parents[2]
sys.path.insert(0, str(PHASE_A))
import store as S  # noqa: E402

REGISTRY = REPO / "research_notes/research_loop/registry.json"
V1_DRAFT = REPO / "research_notes/idea_harvest/intake_draft_20261013.json"
MIGRATION_AT = datetime.now(ZoneInfo("America/New_York")).isoformat(
    timespec="seconds")
HARVEST_AT = "2026-10-13T15:06:00-04:00"  # v1 harvest run time (record)

ATTRIBUTIONS = {
    "EXP-20261012-TIMESFM-SPIKE": {
        "family": "ml_price_forecasting",
        "basis": "Registry failure_strategy_family is null for this entry; "
                 "family attributed from the design package §2.3 worked "
                 "example and the Harvest #1 dedupe record, both of which "
                 "treat EXP-20261012-TIMESFM-SPIKE as the ml_price_forecasting "
                 "family test.",
    },
}


def build_backfill():
    raw = REGISTRY.read_bytes()
    blob_sha = "sha256:" + hashlib.sha256(raw).hexdigest()
    registry = json.loads(raw.decode("utf-8"))
    experiments = registry["experiments"]
    fam_populated = sum(1 for e in experiments
                        if e.get("failure_strategy_family")
                        not in (None, "", "N/A"))
    fam_na = sum(1 for e in experiments
                 if e.get("failure_strategy_family") == "N/A")
    fam_null = sum(1 for e in experiments
                   if e.get("failure_strategy_family") in (None, ""))
    id_null = sum(1 for e in experiments if not e.get("experiment_id"))
    counts = S._registry_test_counts(experiments, ATTRIBUTIONS)
    return {
        "artifact": "registry-backfill/1.0.0",
        "generated_at": MIGRATION_AT,
        "generator": S.STORE_VERSION,
        "registry_pin": {
            "path": "research_notes/research_loop/registry.json",
            "blob_sha256": blob_sha,
            "byte_size": len(raw),
            "experiment_count": len(experiments),
        },
        "coverage_limits": [
            f"Backfill covers ONLY the pinned blob above "
            f"({len(experiments)} experiments). Later registry edits are "
            "invisible to this artifact until the ledger is re-materialized "
            "against a new pin.",
            f"{id_null} registry entries have experiment_id=null; they "
            "cannot serve as last_test_ref and carry no family attribution.",
            f"failure_strategy_family is populated for {fam_populated} of "
            f"{len(experiments)} entries ({fam_na} are the string 'N/A', "
            f"{fam_null} are null). Families below are therefore a LOWER "
            "BOUND on the tested-family record.",
            "Family attribution overrides applied: "
            + json.dumps(ATTRIBUTIONS, ensure_ascii=False),
            "Registry state is free-text: one entry's state field contains "
            "a full verdict sentence (EXP-20261012-TIMESFM-SPIKE). Test "
            "counting uses the documented substring rules in "
            "store._registry_test_counts (FAIL in state, or verdict "
            "starting with FAIL; PASS in state and not failed).",
            "HOLD/REVIEW/proposal states count toward tests_run for their "
            "family but toward neither tests_failed nor tests_passed.",
        ],
        "family_test_counts": {
            fam: {k: v for k, v in c.items() if k != "closed"}
            for fam, c in sorted(counts.items())
        },
        "closed_families": sorted(f for f, c in counts.items() if c["closed"]),
    }


def migrated_card(draft_entry, *, source_overrides, extra_limitations,
                  short_title=True):
    card = {
        "claim": draft_entry["hypothesis"],
        "short_title": draft_entry["title"] if short_title else None,
        "hypothesis": draft_entry["hypothesis"],
        "strategy_family": draft_entry["failure_strategy_family"],
        "timeframe": draft_entry["failure_timeframe"],
        "mechanically_definable": True,
        "pit_data": "yes",
        "pit_inputs": draft_entry.get("dependencies") or [],
        "source": source_overrides,
        "limitations": list(draft_entry.get("limitations") or [])
                       + list(extra_limitations),
        "lane_fit": "daily",
        "created_at": HARVEST_AT,
        "created_by": "idea-harvest-weekly",
        "card_origin": "v1-migration",
        "v1_draft_id": draft_entry["experiment_id"],
    }
    card = {k: v for k, v in card.items() if v is not None}
    return card


def src(authors, title, venue, url, access_basis, evidence, source_class,
        is_primary, **kw):
    base = {
        "authors": authors, "title": title, "venue": venue, "url": url,
        "accessed_at": HARVEST_AT, "access_basis": access_basis,
        "evidence": evidence, "content_hash": None,
        "content_hash_note": "not captured in v1; canonical-text hashing "
                             "begins with Phase A intake",
        "extractor_version": "none-v1", "is_primary": is_primary,
        "source_class": source_class, "doi": "",
    }
    base.update(kw)
    return base


PARKED_NOTE = ("Primary source class is PARKED-SOURCE under Phase A rules "
               "(sources #2/#4/#5): a primary source of record must replace "
               "the summary/mirror before this card can be newly "
               "shortlisted on that primary alone.")


def build_migration_store(backfill):
    store_root = HERE / "store"
    if store_root.exists() and any(store_root.iterdir()):
        raise SystemExit(f"migration store already exists: {store_root} "
                         "(refusing to overwrite)")
    clock = lambda: MIGRATION_AT  # noqa: E731
    st = S.Store(store_root, clock=clock)
    st.init_layout()
    run = st.new_run_id()
    st.acquire_lease(run)
    st.append_event("RUN_START", run,
                    extra={"migration": "HARVEST-20261013 (v1 intake draft "
                                        "+ rejected-at-dedupe records)"})
    v1 = json.loads(V1_DRAFT.read_text(encoding="utf-8"))
    drafts = {e["experiment_id"]: e for e in v1["experiments"]}
    rank_note = {"rubric": "v1 ordinal ranking only; per-criterion "
                           "subscores were not recorded in v1"}

    def migrate(entry, source, rank, terminal, extra_events=(),
                extra_limitations=()):
        card = migrated_card(entry, source_overrides=source,
                             extra_limitations=extra_limitations)
        errs = S.validate_card(
            {**card, "idea_id": "IDEA-0000-0000",
             "claim_normalized": S.normalize_claim(card["claim"]),
             "dedup_key": "sha256:" + "0" * 64},
            st.sources_idx, new_intake=False)
        assert not errs, (entry["experiment_id"], errs)
        card["idea_id"] = f"IDEA-2026-{st.next_idea_seq():04d}"
        card["claim_normalized"] = S.normalize_claim(card["claim"])
        card["dedup_key"] = S.dedup_key(card["claim_normalized"],
                                        card["source"])
        st.write_card(card)
        st.append_event("MIGRATED", run, idea_id=card["idea_id"],
                        from_state="DISCOVERED", to_state="INGESTED",
                        reason=f"migrated from v1 intake draft "
                               f"{entry['experiment_id']} "
                               f"(HARVEST-20261013)")
        if rank is not None:
            st.append_event("RANKED", run, idea_id=card["idea_id"],
                            from_state="INGESTED", to_state="RANKED",
                            rank=rank, score_breakdown=rank_note)
        for ev in extra_events:
            st.append_event(ev["event_type"], run, idea_id=card["idea_id"],
                            reason=ev["reason"])
        if terminal:
            st.transition(card["idea_id"], terminal[0], run,
                          reason=terminal[1])
        return card["idea_id"]

    d = drafts["DRAFT-20261013-IH01-OVERNIGHT-INTRADAY-DECOMPOSITION"]
    migrate(d, src("Lou, Polk & Skouras",
                   "A Tug of War: Overnight versus Intraday Expected Returns",
                   "Journal of Financial Economics 134 (2019), 192–213",
                   "https://researchonline.lse.ac.uk/id/eprint/87481/",
                   "open-access author manuscript (LSE Research Online)",
                   "Working-paper record and abstract state the "
                   "overnight/intraday expected-return decomposition and "
                   "its persistence.",
                   "SRC-OA-REPOSITORIES", True, parked_primary_source=True),
            1, ("SHORTLISTED", None), extra_limitations=[PARKED_NOTE])

    d = drafts["DRAFT-20261013-IH02-LOTTERY-MAX"]
    migrate(d, src("Bali, Cakici & Whitelaw",
                   "Maxing Out: Stocks as Lotteries and the Cross-Section "
                   "of Expected Returns",
                   "Journal of Financial Economics 99 (2011), 427–446",
                   "https://paperswithbacktest.com/api/paper/maxing-out-"
                   "stocks-as-lotteries-and-the-cross-section-of-expected/"
                   "pdf",
                   "secondary replication summary PDF (Papers With "
                   "Backtest) — v1 fetched the paper PDF via this mirror",
                   "Harvest #1: claim as published (MAX effect); working "
                   "paper also at SSRN abstract 1262416.",
                   "SRC-PAPERS-WITH-BACKTEST", True,
                   parked_primary_source=True),
            2, ("SHORTLISTED", None), extra_limitations=[PARKED_NOTE])

    d = drafts["DRAFT-20261013-IH03-VOLUME-PREMIUM"]
    migrate(d, src("Gervais, Kaniel & Mingelgrin",
                   "The High-Volume Return Premium",
                   "Journal of Finance 56 (2001), 877–919",
                   "https://sites.duke.edu/sgervais/research/"
                   "gervais-kaniel-mingelgrin-2001/",
                   "author research page — reference and abstract",
                   "Author page carries the paper reference and abstract "
                   "stating the high-volume return premium.",
                   "SRC-OA-REPOSITORIES", True, parked_primary_source=True),
            3, ("SHORTLISTED", None), extra_limitations=[PARKED_NOTE])

    d = drafts["DRAFT-20261013-IH04-ANCHORING-MOMENTUM"]
    migrate(d, src("George & Hwang",
                   "The 52-Week High and Momentum Investing",
                   "Journal of Finance 59 (2004), 2145–2176",
                   "https://blankcapitalresearch.com/learn/"
                   "george-hwang-52-week-high",
                   "secondary research summary — the v1 run fetched the "
                   "summary, not the primary paper",
                   "Summary states the nearness-to-52-week-high claim and "
                   "that it reportedly subsumes return momentum.",
                   "SRC-FACTOR-SUMMARIES", False),
            4, ("SHORTLISTED", None),
            extra_events=[{
                "event_type": "ADJACENCY_FLAG",
                "reason": "v1 adjacency flag: momentum-family adjacent "
                          "(V5.4 trend_4h FAIL) but different statistic "
                          "(price/rolling-max) and mechanism; novelty "
                          "discounted; human confirmation, no automated "
                          "verdict"}],
            extra_limitations=[
                "Primary of record (George & Hwang, JF 2004) was not "
                "itself fetched in v1; this card rests on a secondary "
                "summary — recorded, not hidden."])

    d = drafts["DRAFT-20261013-IH05-INTRADAY-MOMENTUM"]
    migrate(d, src("Gao, Han, Li & Zhou",
                   "Market Intraday Momentum",
                   "Journal of Financial Economics (2018); SSRN 2552752",
                   "https://paperswithbacktest.com/api/paper/"
                   "intraday-momentum-the-first-half-hour-return-predicts-"
                   "the-last-half-hour-return/pdf",
                   "secondary replication summary PDF (Papers With "
                   "Backtest) — v1 fetched the paper PDF via this mirror",
                   "Harvest #1: first half-hour return predicts the last "
                   "half-hour return.",
                   "SRC-PAPERS-WITH-BACKTEST", True,
                   parked_primary_source=True),
            5, ("BLOCKED-DATA",
                "PIT data route unmet: qualified 30-minute bar history "
                "unavailable (intraday data wall). Ranked 5th in v1 "
                "shortlist with this caveat recorded; classified "
                "BLOCKED-DATA under the design §3.1 archetype."),
            extra_limitations=[PARKED_NOTE])

    d = drafts["DRAFT-20261013-IH06-VOLATILITY-FORECAST"]
    migrate(d, src("Zadourian & Grassberger",
                   "Asymmetry of Cross Correlations Between Intraday and "
                   "Overnight Volatilities",
                   "arXiv:1509.08079 (2015)",
                   "https://arxiv.org/pdf/1509.08079",
                   "arXiv full-text PDF",
                   "Paper states the one-way overnight->intraday "
                   "volatility predictability.",
                   "SRC-ARXIV-QFIN", True),
            6, ("BLOCKED-DATA",
                "PIT data route unmet: realized intraday volatility at "
                "length needs intraday bar history (same wall as rank 5). "
                "Ranked 6th in v1 shortlist with this caveat recorded."))

    # -- the two v1 dedupe-rejected candidates (failure memory) ----------
    rej1 = {
        "experiment_id": "V1-REJECTED-ML-FORECASTING",
        "title": "Supervised ML trend forecasting (v1 dedupe reject)",
        "hypothesis": "Supervised ML models (e.g. LSTM feature stacks on "
                      "SMA/volatility/RSI/MACD) forecast price/trend well "
                      "enough to trade.",
        "failure_strategy_family": "ml_price_forecasting",
        "failure_timeframe": "Model-dependent; evaluated as daily "
                             "forecasting claim",
        "dependencies": [],
        "limitations": ["Rejected at dedupe in Harvest #1; migrated for "
                        "failure memory only."],
    }
    c1 = migrated_card(
        rej1,
        source_overrides=src(
            "E-TRENDS authors (as cited in Harvest #1)",
            "E-TRENDS (LSTM forecasting paper, arXiv HTML)",
            "arXiv (as fetched in Harvest #1)",
            "https://arxiv.org/html/2603.14453v1",
            "arXiv HTML full text",
            "Harvest #1 record: ML model forecasts price/trend from "
            "engineered price features.",
            "SRC-ARXIV-QFIN", True),
        extra_limitations=[])
    c1["lane_fit"] = "none"
    c1["idea_id"] = f"IDEA-2026-{st.next_idea_seq():04d}"
    c1["claim_normalized"] = S.normalize_claim(c1["claim"])
    c1["dedup_key"] = S.dedup_key(c1["claim_normalized"], c1["source"])
    st.write_card(c1)
    st.append_event("MIGRATED", run, idea_id=c1["idea_id"],
                    from_state="DISCOVERED", to_state="INGESTED",
                    reason="migrated from Harvest #1 rejected-at-dedupe "
                           "record (no v1 draft entry existed)")
    st.transition(c1["idea_id"], "REJECTED", run,
                  reason="Family match: supervised ML price/trend "
                         "forecasting = EXP-20261012-TIMESFM-SPIKE family "
                         "(CLOSED-FAIL); variation, not a new mechanism "
                         "(v1 dedupe rule 2). Seed "
                         "KILLED-ML-PRICE-FORECASTING.")

    rej2 = {
        "experiment_id": "V1-REJECTED-PLAIN-MOMENTUM",
        "title": "Plain return momentum (v1 dedupe reject)",
        "hypothesis": "Plain cross-sectional / time-series return "
                      "momentum (12-1 momentum, TSMOM) earns a tradable "
                      "premium.",
        "failure_strategy_family": "trend_momentum",
        "failure_timeframe": "Daily/weekly momentum formation",
        "dependencies": [],
        "limitations": ["Rejected at dedupe in Harvest #1; migrated for "
                        "failure memory only.",
                        "No source URL was recorded in the v1 harvest for "
                        "this generic claim class."],
    }
    c2 = migrated_card(
        rej2,
        source_overrides=src(
            "not recorded in v1",
            "Plain return momentum (generic claim class)",
            "generic — no single source recorded in v1",
            None,
            "not captured — no source URL recorded in v1 harvest",
            "Harvest #1 record: generic momentum on a new lookback or "
            "universe is a retune of the most-tested family.",
            None, False,
            url_note="source.url is null: v1 recorded no URL for this "
                     "rejected generic claim class"),
        extra_limitations=[])
    c2["lane_fit"] = "none"
    c2["idea_id"] = f"IDEA-2026-{st.next_idea_seq():04d}"
    c2["claim_normalized"] = S.normalize_claim(c2["claim"])
    c2["dedup_key"] = S.dedup_key(c2["claim_normalized"], c2["source"])
    st.write_card(c2)
    st.append_event("MIGRATED", run, idea_id=c2["idea_id"],
                    from_state="DISCOVERED", to_state="INGESTED",
                    reason="migrated from Harvest #1 rejected-at-dedupe "
                           "record (no v1 draft entry existed)")
    st.transition(c2["idea_id"], "REJECTED", run,
                  reason="Attempted variation: trend/momentum is the "
                         "registry's most-tested family (V5.4 trend_4h "
                         "standing FAIL; corrected-grid -15.23R adverse "
                         "evidence preserved). Seed "
                         "KILLED-TREND-MOMENTUM-REPARAM.")

    st.append_event("RUN_END", run)
    st.verify_chain()
    # Materializers are lease-fenced mutations: run them BEFORE releasing.
    drafts_path = S.materialize_drafts(st, run)
    ledger_path = S.materialize_ledger(
        st, REGISTRY, attributions=ATTRIBUTIONS,
        out_path=store_root / "ledger" / "family_ledger.json")
    st.release_lease()
    return run, drafts_path, ledger_path


def main():
    before = hashlib.sha256(REGISTRY.read_bytes()).hexdigest()
    backfill = build_backfill()
    out = HERE / "registry_backfill.json"
    S._write_deterministic(out, backfill)
    run, drafts_path, ledger_path = build_migration_store(backfill)
    after = hashlib.sha256(REGISTRY.read_bytes()).hexdigest()
    assert before == after, "registry.json changed during migration!"
    pin = backfill["registry_pin"]["blob_sha256"]
    closed = backfill["closed_families"]
    print(f"backfill: {out} (registry pin {pin[:23]}..., "
          f"closed families: {closed}")
    print(f"migration store: {HERE / 'store'} (run {run})")
    print(f"drafts: {drafts_path}")
    print(f"ledger: {ledger_path}")
    print(f"registry.json unchanged: {before[:16]} == {after[:16]}")


if __name__ == "__main__":
    main()
