"""QF-EQUITY43-S1-CAUSALITY-GUARDS-20261023-17 r2 — successor
fail-closed RESULT reporter (succeeds report17.py of r1).

Governing text: Issue #1 comment 6380534722. ChatGPT's independent
source review of r1 found ONE remaining gap: report17.py accepted
any free-form `inventory.pins` string beginning with "PASS" — the
r1 artifact carried only "PASS (ref P0/P1 as -15)" — so the actual
source/data/receipt/session-table/PAUSED pin evidence could be
missing or changed while the reporter still passed.

This reporter closes that gap and changes NOTHING else:

  * `sections.inventory` must be exactly
    {"pin_inventory_version": "structured-v1", "pins": {...}} where
    `pins` is a STRUCTURED object whose key set equals
    EXPECTED_PIN_INVENTORY's exactly (missing, renamed or extra keys
    fail) and whose every value equals the pinned expected value
    exactly (nested dicts compared by deep equality). A free-form
    string — forged or genuine — is refused outright.
  * the inventory's experiment/sector pins must also agree with the
    `config_pins` section (defense in depth; both are independently
    pinned to the same constants).
  * every other check is report17.py's, unchanged: complete section
    inventory, config pins and frozen simulator constants, reference
    cohort 586/4/590 + cutoff, observer stream/journal binding, bars
    44,849 + VWAP tolerance, benchmark 524 equal, closes identity,
    field census over exactly the 12 simulator-consumed fields with
    detail.compared == 590 and only the documented `censored`
    key-presence residual tolerated, decision parity (RS 0, decisions
    0, terminal inventories deep-equal, C0 == {193, 323, 74} on BOTH
    sides), reference self-check, no recorded problems, recorded
    verdict == re-derived verdict.

Usage: report17r2.py <compare.json> <out_RESULT.md>
Exit 0 only when the re-derived verdict is DECISION_PARITY_PASS.
"""
import json
import sys

EXPECTED_FIELDS = ["entry", "stop", "tp1", "exit", "entry_time",
                   "exit_time", "signal_time", "reason", "hold_bars",
                   "tp1_hit", "censored", "risk_frac"]
REQUIRED_SECTIONS = ["inventory", "config_pins", "reference",
                     "observer_stream", "bars_parity",
                     "benchmark_parity", "closes_identity",
                     "field_census", "decision_parity",
                     "reference_selfcheck"]
EXPECTED_CONFIG_SHA = \
    "87b8285a522ba0e3e5a80f0097b9668afc1ddf11da4fc5559c0ca31f55218706"
EXPECTED_SECTOR_SHA = \
    "a91222c7a27e83d279bdf162de5dfc030a88911d65b0ee43ea196ee38a7cea2c"
EXPECTED_C0 = {"taken_count": 193, "skipped_cap": 323, "skipped_risk": 74}
EXPECTED_COUNTS = {"symbols": 43, "bars": 44849, "sessions": 524,
                   "closed": 586, "censored": 4, "total": 590,
                   "compared": 590, "raw_rows": 157140,
                   "skipped_gap": 1}
# The structured exact pin inventory (r2). Every value is the frozen
# P0/P1 record of the -13/-15/-16/-17 chain, recomputed by
# emit_inventory17r2.py from the committed stage sources.
EXPECTED_PIN_INVENTORY = {
    "observer_module": "fwd_observer17.py",
    "observer_module_sha256":
        "929c1bc4cac34384ad0a8807a1006aaafc555f5b6cf548f5f030ef26110052c3",
    "source_pins": {
        "engine_successor/pine_backtest.py":
            "874d2a9b1d99171a4d3db709ece9ce4719b4d108a70f7e95b4a082692cc0c99d",
        "engine_successor/pine_stack/pine_stack.py":
            "8d4a964fd7bb08b4a98a55eb7fae222157ae27f1a768f255e7cbc152c9d15b03",
        "engine_fork09/pine_backtest.py":
            "becea0824486003daef386b49e137a83ffdf22c1e2d145136498919102fc42f2",
        "engine_fork09/pine_stack/pine_stack.py":
            "30594231ffc3bac27303f96310e8f274229415c890c371f4dbdfcdb54156cda4",
        "asof_benchmark.py":
            "f0f4582c4a8aee484c24d330658b0c4ae6e2a169c19f3bf2b1475c2dc2ce2017",
        "engine_successor/scanner_rules.py":
            "62aa743ac28f05de9b6ec0ab962ee28bb7e5152bbef00bff5afa611a480f473c",
        "engine_successor/pine_ranking/pine_ranking.py":
            "77afae0df120e3a2ad77a6d2d43247c8aea0ad296f08c273bff7d1cc833aaae6",
        "engine_successor/pine_signal_quality/pine_signal_quality.py":
            "b1b39ee8d0bd4bbb1387b3ce54c7345c1f8dd622f94a5ed390c989fed1d39e69",
        "engine_successor/pine_exposure/pine_exposure.py":
            "9f646161c27f6b28febe0980d03665bc9c1502fb844d37be6fd1d72ee45102be",
        "engine_fork09/scanner_rules.py":
            "62aa743ac28f05de9b6ec0ab962ee28bb7e5152bbef00bff5afa611a480f473c",
        "engine_fork09/pine_ranking/pine_ranking.py":
            "77afae0df120e3a2ad77a6d2d43247c8aea0ad296f08c273bff7d1cc833aaae6",
        "engine_orig/pine_backtest.py":
            "447a9a13bb2ec7ab0be246fdf6d3f2df06633bc6cb7fbdb76a24e23935d160e5",
        "engine_orig/pine_stack/pine_stack.py":
            "839e4800624de253514095b5c007e8088afc0ab6c6ef45c86fb29a5956dfcefa",
        "session_table.json":
            "00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f",
    },
    "experiment_config_sha256": EXPECTED_CONFIG_SHA,
    "sector_map_sha256": EXPECTED_SECTOR_SHA,
    "child_manifest_root_sha256":
        "c5628652c5bf59d870103e41fd7e22a23fe4d811c61662fda78a8790abd0444f",
    "parent_manifest_root_sha256":
        "ca49892062f1ac5d4ec6d20eaadd37b519aec84ad0b23a995fb11db74dccfd64",
    "pilot_manifest_root_sha256":
        "79ccdd128e0b36537f56f8ae36a731b719e989b9756f65856b7dc47344327122",
    "child_chain_receipts_verified": 54,
    "child_chain_head":
        "c129e95fc404deff12310fe39048c8c610b93f2f976dbb321754ea86340ca6cc",
    "legs_without_receipt_quarantined": 23,
    "pilot_receipts": {
        "NVDA": {"response_sha256":
                 "b1ecf7bf6718cda1c1cd4fa0da4a1281bc14cc6c4fc1d357aaeabaa77d3fa0f6",
                 "rows": 3654},
        "TSLA": {"response_sha256":
                 "f6b1e64f244b06543f536be8eaf04d731b7dd98700bf1afdbb7ff59b303479fe",
                 "rows": 3655},
        "AAPL": {"response_sha256":
                 "97649d2f2a326b8a2e2e20a72cfaa83ebfaaed128698f1829716d37506acdd4f",
                 "rows": 3655},
        "SPY": {"response_sha256":
                "2c6631dc5482b5f8e20a2107b53fbcd64e1ae3732d2bf09adf17c874076fecfb",
                "rows": 3655},
    },
    "archive_continue11_files": 158,
    "archive_continue11_mismatches": [],
    "archive_pilot_files": 22,
    "archive_pilot_mismatches": [],
    "paused_harness_sha256":
        "ce7c902ce182683ca1723468a0109747abd80db287c39556ea4db78210a0833d",
    "pause_new_entries_present": True,
    "resume_new_entries_present": False,
}
STOP = "STOP_DECISION_PARITY_FAILURE"
PASS = "DECISION_PARITY_PASS"


def pin_reasons(inv):
    """Exact structured pin-inventory validation. Anything that is
    not the complete structured inventory with exact values fails."""
    reasons = []
    if not isinstance(inv, dict):
        return ["inventory section is not an object"]
    if set(inv) != {"pin_inventory_version", "pins"}:
        reasons.append(
            "inventory key set != {pin_inventory_version, pins}: "
            f"{sorted(inv)}")
    if inv.get("pin_inventory_version") != "structured-v1":
        reasons.append("pin_inventory_version="
                       f"{inv.get('pin_inventory_version')!r} "
                       "!= 'structured-v1'")
    pins = inv.get("pins")
    if not isinstance(pins, dict):
        reasons.append(
            "inventory.pins is not a structured object — free-form "
            f"pin labels are refused: {pins!r:.80}")
        return reasons
    want_keys = set(EXPECTED_PIN_INVENTORY)
    if set(pins) != want_keys:
        reasons.append(
            "pin key set differs: missing="
            f"{sorted(want_keys - set(pins))} extra="
            f"{sorted(set(pins) - want_keys)}")
        return reasons
    for k, want in EXPECTED_PIN_INVENTORY.items():
        if pins.get(k) != want:
            reasons.append(f"pin {k} != its exact expected value")
    return reasons


def derive(doc):
    """Return (verdict, reasons) re-derived from the FULL required
    inventory. Every check is explicit; anything absent fails."""
    reasons = []
    if not isinstance(doc, dict):
        return STOP, ["document is not an object"]
    sec = doc.get("sections")
    if not isinstance(sec, dict):
        return STOP, ["no sections object"]

    def need(name):
        if name not in sec:
            reasons.append(f"missing section: {name}")
            return None
        if not isinstance(sec[name], dict) or not sec[name]:
            reasons.append(f"empty section: {name}")
            return None
        return sec[name]

    for name in REQUIRED_SECTIONS:
        need(name)

    inv = sec.get("inventory")
    if isinstance(inv, dict):
        reasons.extend(pin_reasons(inv))

    cfg = sec.get("config_pins")
    if isinstance(cfg, dict):
        if cfg.get("experiment_config_sha256") != EXPECTED_CONFIG_SHA:
            reasons.append("config sha != pinned 87b8285a...")
        if cfg.get("experiment_config_sha_match") is not True:
            reasons.append("config pin not matched")
        if cfg.get("sector_map_sha256") != EXPECTED_SECTOR_SHA:
            reasons.append("sector map sha != pinned a91222c7...")
        for k, v in (("start_equity", 10000.0), ("risk_pct", 0.01),
                     ("max_concurrent", 5), ("max_portfolio_risk", 0.05),
                     ("sl_atr", 1.5), ("tp_atr", 2.0), ("trail_atr", 2.5),
                     ("warmup", 215)):
            if cfg.get(k) != v:
                reasons.append(f"config {k}={cfg.get(k)!r} != {v!r}")
        if cfg.get("costs") != {"4bps": 0.0004, "25bps": 0.0025}:
            reasons.append(f"config costs={cfg.get('costs')!r}")
        # defense in depth: the structured inventory's experiment /
        # sector pins must agree with this section exactly
        if isinstance(inv, dict) and isinstance(inv.get("pins"), dict):
            p = inv["pins"]
            if p.get("experiment_config_sha256") != \
                    cfg.get("experiment_config_sha256"):
                reasons.append("inventory experiment pin disagrees "
                               "with config_pins section")
            if p.get("sector_map_sha256") != \
                    cfg.get("sector_map_sha256"):
                reasons.append("inventory sector pin disagrees with "
                               "config_pins section")

    refsec = sec.get("reference")
    if isinstance(refsec, dict):
        if refsec.get("closed_candidates") != EXPECTED_COUNTS["closed"]:
            reasons.append("reference closed_candidates="
                           f"{refsec.get('closed_candidates')} != 586")
        if refsec.get("censored_candidates") != \
                EXPECTED_COUNTS["censored"]:
            reasons.append("reference censored_candidates="
                           f"{refsec.get('censored_candidates')} != 4")
        if refsec.get("total_candidates") != EXPECTED_COUNTS["total"]:
            reasons.append("reference total_candidates="
                           f"{refsec.get('total_candidates')} != 590")
        if refsec.get("skipped_gap_below_stop") != \
                EXPECTED_COUNTS["skipped_gap"]:
            reasons.append("reference skipped_gap_below_stop="
                           f"{refsec.get('skipped_gap_below_stop')} != 1")
        if not refsec.get("cutoff"):
            reasons.append("reference cutoff missing")

    obs = sec.get("observer_stream")
    if isinstance(obs, dict):
        if obs.get("raw_rows") != EXPECTED_COUNTS["raw_rows"]:
            reasons.append(f"observer raw_rows={obs.get('raw_rows')} "
                           "!= 157140")
        if obs.get("rejected") != 0:
            reasons.append(f"observer rejected={obs.get('rejected')}")
        if obs.get("journal_verify") is not True:
            reasons.append("journal not verified")
        ji = obs.get("journal_info")
        if not isinstance(ji, dict) or not ji.get("head"):
            reasons.append("observer journal_info missing/headless")
        else:
            if ji.get("records") != obs.get("journal_records"):
                reasons.append("journal_records != journal_info.records")
            if obs.get("anchor_head") != str(ji.get("head"))[:16]:
                reasons.append("anchor_head != journal head prefix")
        if not (isinstance(obs.get("decision_events"), int)
                and obs["decision_events"] > 0):
            reasons.append("observer decision_events not positive")

    bars = sec.get("bars_parity")
    if isinstance(bars, dict):
        if bars.get("bars_compared") != EXPECTED_COUNTS["bars"]:
            reasons.append(f"bars_compared={bars.get('bars_compared')} "
                           "!= 44849")
        if bars.get("symbols_bad") != 0:
            reasons.append(f"bars symbols_bad={bars.get('symbols_bad')}")
        v = bars.get("sessionvwap_max_abs_diff")
        if not (isinstance(v, (int, float)) and v <= 1e-9):
            reasons.append(f"sessionvwap diff {v!r} above tolerance")

    bench = sec.get("benchmark_parity")
    if isinstance(bench, dict):
        if bench.get("equal") is not True:
            reasons.append("benchmark not equal")
        if bench.get("sessions") != EXPECTED_COUNTS["sessions"]:
            reasons.append(f"benchmark sessions={bench.get('sessions')}"
                           " != 524")

    closes = sec.get("closes_identity")
    if isinstance(closes, dict):
        if closes.get("symbols_compared") != EXPECTED_COUNTS["symbols"]:
            reasons.append("closes symbols_compared="
                           f"{closes.get('symbols_compared')} != 43")
        if closes.get("symbols_bad") != 0:
            reasons.append("closes symbols_bad="
                           f"{closes.get('symbols_bad')}")
        if closes.get("max_abs_diff") != 0.0:
            reasons.append("closes identity not exact")

    census = sec.get("field_census")
    if isinstance(census, dict):
        pf = census.get("per_field")
        detail = census.get("detail")
        if not isinstance(pf, dict) or set(pf) != set(EXPECTED_FIELDS):
            reasons.append("field_census per_field key set != the 12 "
                           "simulator-consumed fields: "
                           f"{sorted(pf) if isinstance(pf, dict) else pf!r}")
            pf = pf if isinstance(pf, dict) else {}
        if not isinstance(detail, dict) \
                or set(detail) != set(EXPECTED_FIELDS):
            reasons.append("field_census detail key set != the 12 "
                           "simulator-consumed fields")
            detail = detail if isinstance(detail, dict) else {}
        for f in EXPECTED_FIELDS:
            d = detail.get(f)
            if isinstance(d, dict):
                if d.get("compared") != EXPECTED_COUNTS["compared"]:
                    reasons.append(f"detail.{f}.compared="
                                   f"{d.get('compared')} != 590")
                if f in pf and d.get("mismatches") != pf.get(f):
                    reasons.append(f"detail.{f}.mismatches="
                                   f"{d.get('mismatches')} != per_field "
                                   f"{pf.get(f)}")
            if f != "censored" and f in pf and pf.get(f) != 0:
                reasons.append(f"consumed field {f} mismatches="
                               f"{pf.get(f)}")
        if isinstance(pf, dict) and pf and \
                census.get("total_mismatches") != sum(pf.values()):
            reasons.append("field_census total_mismatches != "
                           "sum(per_field)")
        if census.get("keyset_problems") != []:
            reasons.append("field_census keyset_problems="
                           f"{census.get('keyset_problems')}")
        if census.get("extra_key_asymmetry") not in ([], ["censored"]):
            reasons.append("field_census extra_key_asymmetry="
                           f"{census.get('extra_key_asymmetry')}")
        # documented censored key-presence artifact only (as report16)
        if isinstance(pf, dict) and pf and \
                census.get("total_mismatches") != pf.get("censored", 0):
            reasons.append("field census residual outside the "
                           "documented censored artifact")

    dec = sec.get("decision_parity")
    if isinstance(dec, dict):
        if dec.get("rs_mismatches") != 0:
            reasons.append(f"rs_mismatches={dec.get('rs_mismatches')}")
        if dec.get("decision_mismatches") != 0:
            reasons.append("decision_mismatches="
                           f"{dec.get('decision_mismatches')}")
        if dec.get("terminal_symbol_mismatch_views") != []:
            reasons.append("terminal mismatch views="
                           f"{dec.get('terminal_symbol_mismatch_views')}")
        if dec.get("terminal_observer") != dec.get("terminal_reference"):
            reasons.append("terminal inventories differ")
        if dec.get("c0_counts_observer") != EXPECTED_C0:
            reasons.append("C0 observer counts="
                           f"{dec.get('c0_counts_observer')} != 193/323/74")
        if dec.get("c0_counts_reference") != EXPECTED_C0:
            reasons.append("C0 reference counts="
                           f"{dec.get('c0_counts_reference')} != 193/323/74")

    selfchk = sec.get("reference_selfcheck")
    if isinstance(selfchk, dict):
        if selfchk.get("rs_mismatches") != 0 \
                or selfchk.get("decision_mismatches") != 0 \
                or selfchk.get("c0_match") is not True \
                or selfchk.get("terminal_mismatch_views") != []:
            reasons.append("reference self-check not clean")
        if selfchk.get("c0_counts") != EXPECTED_C0:
            reasons.append("self-check C0 counts="
                           f"{selfchk.get('c0_counts')} != 193/323/74")

    if doc.get("problems"):
        reasons.append(f"recorded problems: {doc['problems'][:3]}")
    derived = PASS if not reasons else STOP
    if doc.get("verdict") != derived:
        reasons.append(f"recorded verdict {doc.get('verdict')!r} != "
                       f"re-derived {derived!r}")
        derived = STOP
    return derived, reasons


def main():
    src, out_path = sys.argv[1], sys.argv[2]
    try:
        with open(src) as f:
            doc = json.load(f)
    except Exception as e:  # unparseable / missing = STOP, never PASS
        verdict, reasons = STOP, [f"comparison artifact unreadable: {e}"]
    else:
        verdict, reasons = derive(doc)
    lines = [f"VERDICT (re-derived by report17r2 from the artifact): "
             f"{verdict}"]
    if reasons:
        lines.append("REASONS:")
        lines += [f"- {r}" for r in reasons]
    else:
        lines.append("Complete required inventory present, including "
                     "the structured exact pin inventory; every "
                     "recorded value re-derives to zero mismatches; "
                     "recorded verdict agrees.")
    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if verdict == PASS else 2


if __name__ == "__main__":
    sys.exit(main())
