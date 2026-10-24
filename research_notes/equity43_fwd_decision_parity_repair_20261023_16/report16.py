"""QF-EQUITY43-FWD-DECISION-PARITY-REPAIR-20261023-16 — fail-closed
RESULT reporter.

The -15 failure mode was a wrapper/misread: the comparison JSON recorded
STOP_DECISION_PARITY_FAILURE (201 decision mismatches) while the RESULT
reported PASS from a wrapper signal. This reporter makes that
structurally impossible in the -16 reporting path:

  * it READS the comparison JSON artifact itself (never a wrapper exit
    code, never stdout prose);
  * it RE-DERIVES the verdict from the recorded section values:
    every mismatch count must be exactly 0, every equality flag true,
    the journal verified, the reference self-check clean, and the
    recorded verdict string must agree with the re-derived one;
  * ANY inconsistency — missing file, unparseable JSON, missing
    section, nonzero count, verdict/count disagreement — yields a
    STOP RESULT and exit code 2. Absence of evidence is failure.

Usage: report16.py <compare16.json> <out_RESULT.md>
Exit 0 only when the re-derived verdict is DECISION_PARITY_PASS.
"""
import json
import sys


def derive(doc):
    """Return (verdict, reasons) re-derived from section values only."""
    reasons = []
    if not isinstance(doc, dict):
        return "STOP_DECISION_PARITY_FAILURE", ["document is not an object"]
    sec = doc.get("sections")
    if not isinstance(sec, dict):
        return "STOP_DECISION_PARITY_FAILURE", ["no sections object"]

    def need(name):
        if name not in sec:
            reasons.append(f"missing section: {name}")
            return None
        return sec[name]

    inv = need("inventory")
    cfg = need("config_pins")
    if cfg is not None and cfg.get("experiment_config_sha_match") is not True:
        reasons.append("config pin not matched")
    bars = need("bars_parity")
    if bars is not None:
        if bars.get("symbols_bad") != 0:
            reasons.append(f"bars symbols_bad={bars.get('symbols_bad')}")
        if not (bars.get("sessionvwap_max_abs_diff", 1) <= 1e-9):
            reasons.append("sessionvwap diff above tolerance")
    bench = need("benchmark_parity")
    if bench is not None and bench.get("equal") is not True:
        reasons.append("benchmark not equal")
    closes = need("closes_identity")
    if closes is not None:
        if closes.get("symbols_bad") != 0 or closes.get("max_abs_diff") != 0.0:
            reasons.append("closes identity not exact")
    census = need("field_census")
    if census is not None:
        # Simulator-consumption semantics, per the PASS bar's own
        # wording ("all simulator-consumed fields"): every consumed
        # field VALUE must match, and the only tolerated strict-
        # comparison residual is the documented `censored` key-presence
        # artifact — the reference/frozen generator omits the key on
        # closed candidates (None) while the observer writes False
        # explicitly, and the simulator consumes the field solely via
        # tr.get("censored") truthiness (pine_stack.py line 70), so the
        # consumed values are identical. Strict dict equality is
        # unachievable by construction without touching frozen code;
        # ANY other strict residual fails closed here.
        pf = census.get("per_field", {})
        other = sum(v for k, v in pf.items() if k != "censored")
        residual_ok = (
            census.get("keyset_problems") == []
            and census.get("extra_key_asymmetry") in ([], ["censored"])
            and census.get("total_mismatches") == pf.get("censored", 0))
        if other != 0 or not residual_ok:
            reasons.append(
                "field census: consumed-field mismatches outside the "
                f"documented censored artifact: other={other}, "
                f"total={census.get('total_mismatches')}, "
                f"censored_strict={pf.get('censored')}")
    dec = need("decision_parity")
    if dec is not None:
        if dec.get("rs_mismatches") != 0:
            reasons.append(f"rs_mismatches={dec.get('rs_mismatches')}")
        if dec.get("decision_mismatches") != 0:
            reasons.append(
                f"decision_mismatches={dec.get('decision_mismatches')}")
        if dec.get("terminal_symbol_mismatch_views") not in ([], None) \
                and dec.get("terminal_symbol_mismatch_views"):
            reasons.append("terminal inventory mismatch views="
                           f"{dec.get('terminal_symbol_mismatch_views')}")
        if dec.get("c0_counts_observer") != dec.get("c0_counts_reference"):
            reasons.append("C0 counts differ")
    selfchk = need("reference_selfcheck")
    if selfchk is not None:
        if selfchk.get("decision_mismatches") != 0 \
                or selfchk.get("rs_mismatches") != 0 \
                or selfchk.get("c0_match") is not True \
                or selfchk.get("terminal_mismatch_views"):
            reasons.append("reference self-check not clean")
    obs = need("observer_stream")
    if obs is not None:
        if obs.get("journal_verify") is not True:
            reasons.append("journal not verified")
        if obs.get("rejected") != 0:
            reasons.append(f"observer rejected={obs.get('rejected')}")
    if doc.get("problems"):
        reasons.append(f"recorded problems: {doc['problems'][:3]}")
    derived = "DECISION_PARITY_PASS" if not reasons else \
        "STOP_DECISION_PARITY_FAILURE"
    if doc.get("verdict") != derived:
        reasons.append(f"recorded verdict {doc.get('verdict')!r} != "
                       f"re-derived {derived!r}")
        derived = "STOP_DECISION_PARITY_FAILURE"
    return derived, reasons


def main():
    src, out_path = sys.argv[1], sys.argv[2]
    try:
        with open(src) as f:
            doc = json.load(f)
    except Exception as e:  # unparseable / missing = STOP, never PASS
        verdict, reasons = "STOP_DECISION_PARITY_FAILURE", \
            [f"comparison artifact unreadable: {e}"]
        doc = None
    else:
        verdict, reasons = derive(doc)
    lines = [f"VERDICT (re-derived by report16 from the artifact): "
             f"{verdict}"]
    if reasons:
        lines.append("REASONS:")
        lines += [f"- {r}" for r in reasons]
    else:
        lines.append("All recorded section values re-derive to zero "
                     "mismatches; recorded verdict agrees.")
    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if verdict == "DECISION_PARITY_PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
