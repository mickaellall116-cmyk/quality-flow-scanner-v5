"""QF-EQUITY43-S1-CAUSALITY-GUARDS-20261023-17 — hardened fail-closed
RESULT reporter (successor to report16.py).

The -16 adjudication found that report16.py is not FULLY fail-closed:
it checks that a `field_census` section exists, but does not require
each expected per-field key, nor `detail.*.compared == 590`, nor the
`reference` section, nor the fixed 43/590/44,849/524 cohort counts, nor
`inventory.pins == PASS` evidence. Deleting `per_field.exit` and
`detail.exit` from the -16 PASS artifact still re-derived PASS there.

This reporter closes the contract: a PASS requires the COMPLETE
inventory below, exactly. Any missing, renamed, emptied or zeroed
section/field/count/pin is a STOP. Absence of evidence is failure.

REQUIRED INVENTORY (all values pinned to the frozen -13/-16 record):
  * sections: inventory, config_pins, reference, observer_stream,
    bars_parity, benchmark_parity, closes_identity, field_census,
    decision_parity, reference_selfcheck — all present;
  * inventory.pins is the recorded PASS evidence string;
  * config pins: experiment sha 87b8285a..., sha_match true, sector map
    sha a91222c7..., and the frozen simulator constants;
  * reference cohort: 586 closed / 4 censored / 590 total candidates,
    1 skipped_gap_below_stop, a recorded cutoff;
  * observer stream: 157,140 raw rows, 0 rejected, journal verified,
    journal record count consistent with its journal_info and anchor;
  * bars parity: 44,849 bars compared, 0 bad symbols, VWAP diff <= 1e-9;
  * benchmark parity: equal, 524 sessions;
  * closes identity: 43 symbols compared, 0 bad, max abs diff 0.0;
  * field census: per_field keys EXACTLY the 12 simulator-consumed
    fields; detail keys EXACTLY the same 12; every detail.compared ==
    590; detail mismatches == per_field counts; total == sum(per_field);
    the only tolerated strict residual is the documented `censored`
    key-presence artifact (consumed via truthiness, pine_stack.py:70);
  * decision parity: rs 0, decisions 0, no terminal mismatch views,
    terminal inventories deep-equal, C0 == {193, 323, 74} on BOTH sides;
  * reference self-check: clean, C0 match true, C0 == {193, 323, 74};
  * no recorded problems; the recorded verdict string must equal the
    re-derived verdict.

Usage: report17.py <compare.json> <out_RESULT.md>
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
STOP = "STOP_DECISION_PARITY_FAILURE"
PASS = "DECISION_PARITY_PASS"


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
        pins = inv.get("pins")
        if not (isinstance(pins, str) and pins.startswith("PASS")):
            reasons.append(f"inventory pins evidence not PASS: {pins!r}")

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
    lines = [f"VERDICT (re-derived by report17 from the artifact): "
             f"{verdict}"]
    if reasons:
        lines.append("REASONS:")
        lines += [f"- {r}" for r in reasons]
    else:
        lines.append("Complete required inventory present; every "
                     "recorded value re-derives to zero mismatches; "
                     "recorded verdict agrees.")
    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if verdict == PASS else 2


if __name__ == "__main__":
    sys.exit(main())
