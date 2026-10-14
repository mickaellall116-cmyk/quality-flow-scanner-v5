#!/usr/bin/env python3
"""Issue #9 prep dry-run tool: schema validation + blind grading + dedupe screen.

OFFLINE, DETERMINISTIC, NO NETWORK, NO MODEL CALLS. This tool grades SYNTHETIC,
prewritten fixture cards only (see fixtures/). In a real run the same machine gates
assist a human auditor, who may override a machine flag only with a written reason
(see grader_packet.md). Machine flags are never final verdicts in a real run.

Usage:
  python3 validate_and_grade.py --package ..   (paths relative to this file by default)
Outputs (into dry_run/):
  anonymized_packet.json  - cards with origin_arm stripped, anon ids, shuffled order
  blinding_key.json       - anon_id -> original hypothesis_id / arm (sealed in real runs)
  dry_run_results.json    - per-card gate detail, verdicts, expected-vs-actual check
  dry_run_ledger_example.json - resource-ledger example (schema-checked; all zeros:
                            the dry run makes no model calls)
"""
import argparse, hashlib, json, random, re, sys
from pathlib import Path

STOPWORDS = set("the a an and or of to in on at is are with without same only bar bars 4h".split())

def tokens(text):
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS and len(t) > 2}

def jaccard(a, b):
    return len(a & b) / max(1, len(a | b))

# ---------- minimal schema validation (stdlib only; mirrors hypothesis_schema.json) ----------
def validate_card(card, schema):
    errs = []
    for f in schema["required"]:
        if f not in card:
            errs.append(f"missing required field: {f}")
    props = schema["properties"]
    for fname, spec in props.items():
        if fname not in card:
            continue
        v = card[fname]
        if spec.get("type") == "string":
            if not isinstance(v, str):
                errs.append(f"{fname}: not a string")
            elif "minLength" in spec and len(v) < spec["minLength"]:
                errs.append(f"{fname}: shorter than minLength {spec['minLength']}")
            if "enum" in spec and v not in spec["enum"]:
                errs.append(f"{fname}: not in enum {spec['enum']}")
        if spec.get("type") == "array" and fname == "required_pit_data":
            if not isinstance(v, list):
                errs.append("required_pit_data: not an array")
            else:
                for i, item in enumerate(v):
                    for rf in ("name", "available_now", "pit_route"):
                        if rf not in item:
                            errs.append(f"required_pit_data[{i}]: missing {rf}")
    d = card.get("declarations")
    if isinstance(d, dict):
        for rf in ("decision_timing", "uses_unavailable_at_decision_data", "materially_different_mechanism"):
            if rf not in d:
                errs.append(f"declarations: missing {rf}")
        if d.get("decision_timing") not in (None, "next_bar_after_completed_bar", "same_bar_close", "other_declared"):
            errs.append("declarations.decision_timing: not in enum")
    if isinstance(card.get("provenance"), str) and "IDEA_ONLY" not in card["provenance"]:
        errs.append("provenance: missing IDEA_ONLY tag (fail-closed exclusion)")
    return errs

def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    ap.add_argument("--package", default=str(here.parent))
    args = ap.parse_args()
    pkg = Path(args.package)

    schema = json.loads((pkg / "hypothesis_schema.json").read_text())
    registry = json.loads((pkg / "killed_family_registry_export.json").read_text())
    ledger_schema = json.loads((pkg / "resource_ledger_schema.json").read_text())
    expected = json.loads((pkg / "fixtures" / "expected_verdicts.json").read_text())["expected_verdicts"]

    fam_disposition = {}
    fam_entry = {}
    for e in registry["entries"]:
        for fam in e["families"]:
            fam_disposition[fam] = e["disposition"]
            fam_entry[fam] = e["entry_id"]

    cards = []
    for arm_file in ("candidates_armA_s1.json", "candidates_armB_s1.json"):
        data = json.loads((pkg / "fixtures" / arm_file).read_text())
        assert data.get("synthetic") is True, "dry-run tool refuses non-synthetic fixtures"
        cards.extend(data["cards"])

    # ---- validate RAW cards first (grader_packet.md step 1): anonymization strips
    # ---- origin_arm, which the schema requires, so validation must precede it. ----
    validation_errors = {c["hypothesis_id"]: validate_card(c, schema) for c in cards}

    # ---- anonymize: strip arm, assign CAND ids, shuffle under recorded seed ----
    shuffle_seed = 9
    order = list(range(len(cards)))
    random.Random(shuffle_seed).shuffle(order)
    packet, key = [], {}
    anon_of = {}
    for pos, idx in enumerate(order, start=1):
        c = dict(cards[idx])
        anon = f"CAND-{pos:03d}"
        anon_of[c["hypothesis_id"]] = anon
        key[anon] = {"hypothesis_id": c["hypothesis_id"], "origin_arm": c["origin_arm"]}
        c.pop("origin_arm", None)
        c["anon_id"] = anon
        packet.append(c)

    # ---- grade (verdict precedence frozen in comparison_protocol.json) ----
    results = []
    accepted = []  # [{family_id, sig(set), anon}] for otherwise-passing cards, in packet order
    for c in packet:
        anon = c["anon_id"]
        orig = key[anon]["hypothesis_id"]
        gates = {}
        errs = validation_errors[orig]
        if errs:
            verdict, detail = "SCHEMA_INVALID", errs
        else:
            d = c["declarations"]
            # G2 leakage (machine assist from declarations)
            if d["decision_timing"] == "same_bar_close" or d["uses_unavailable_at_decision_data"]:
                gates["G2"] = "fail"
                verdict, detail = "FAIL", "G2 leakage: same-bar/unavailable-at-decision data declared"
            elif c["family_id"] in fam_disposition and fam_disposition[c["family_id"]] in ("reject", "reject-new-claims") \
                    and not d["materially_different_mechanism"]:
                gates["G4"] = "fail"
                verdict, detail = "DEDUPE_REJECT", f"G4: family matches registry entry {fam_entry[c['family_id']]}"
            elif any((not it["available_now"]) and not it["pit_route"] for it in c["required_pit_data"]):
                gates["G3"] = "blocked"
                missing = [it["name"] for it in c["required_pit_data"] if not it["available_now"] and not it["pit_route"]]
                verdict, detail = "DATA_BLOCKED", f"G3: unavailable data with no PIT route: {missing}"
            else:
                sig = tokens(c["entry_exit_rules"])
                dup_of = None
                for prev in accepted:
                    if prev["family_id"] == c["family_id"] and jaccard(sig, prev["sig"]) >= 0.45:
                        dup_of = prev["anon"]
                        break
                if dup_of:
                    verdict, detail = "DUPLICATE_OF", f"same family_id + rule signature as {dup_of}"
                else:
                    # G1/G5 machine presence checks (auditor judgment in a real run)
                    if len(c["entry_exit_rules"]) >= 20 and c["null_control_comparator"] and c["preregistered_falsification_test"]:
                        gates.update({"G1": "pass", "G2": "pass", "G3": "pass", "G4": "pass", "G5": "pass"})
                        verdict, detail = "PASS", "all gates pass (machine skeleton; real run adds auditor judgment)"
                        accepted.append({"family_id": c["family_id"], "sig": sig, "anon": anon})
                    else:
                        verdict, detail = "FAIL", "G1: untestable or missing null/falsification"
        exp = expected.get(orig, {})
        results.append({
            "anon_id": anon, "hypothesis_id": orig, "origin_arm": key[anon]["origin_arm"],
            "verdict": verdict, "detail": detail, "gates": gates,
            "expected_verdict": exp.get("verdict"),
            "matches_expected": (verdict == exp.get("verdict")),
        })

    # ---- resource-ledger example: the dry run itself, honestly zero ----
    ledger_example = {
        "run_id": "DRY-RUN-SYNTHETIC-20261014", "arm": "A", "seed": "S1",
        "provider": "NONE (offline prep dry-run)", "model": "NONE", "model_version": "NONE",
        "budget_ref": "ISSUE9-SINGLE-VS-SWARM-PROTOCOL 1.0.0 budgets_per_arm_per_seed",
        "cost_verified_zero_incremental": True,
        "calls": [],
        "totals": {"calls": 0, "billed_tokens": 0, "wall_time_s": 0, "cost_usd": 0.0,
                   "candidate_cards_emitted": 0, "auditor_review_minutes": 0},
        "note": "Structure example validated against resource_ledger_schema.json required fields. "
                "A real run ledger carries one record per arm-seed with per-call lines; this dry run made no calls."
    }
    for f in ledger_schema["required"]:
        assert f in ledger_example, f"ledger example missing {f}"

    # Cluster expectations (cross-arm duplicate pairs): exactly one PASS survivor
    # and one DUPLICATE_OF within the cluster counts as a match for both members.
    by_orig = {r["hypothesis_id"]: r for r in results}
    for r in results:
        exp = expected.get(r["hypothesis_id"], {})
        if exp.get("verdict") == "CLUSTER_SURVIVOR_OR_DUPLICATE":
            members = [by_orig[m] for m in exp["cluster"]]
            verdicts = sorted(m["verdict"] for m in members)
            r["matches_expected"] = verdicts == ["DUPLICATE_OF", "PASS"]
            r["expected_verdict"] = "CLUSTER: one PASS + one DUPLICATE_OF"
    all_match = all(r["matches_expected"] for r in results)
    out = {
        "dry_run_id": "ISSUE9-DRY-RUN-20261014",
        "synthetic": True,
        "meaning": "Pipeline exercise only: proves the validator, blinding, dedupe screen, rubric skeleton and ledger schema work end-to-end on prewritten cards. It is NOT evidence about single-model vs swarm performance; the cards were authored to hit each verdict path.",
        "shuffle_seed": shuffle_seed,
        "cards_graded": len(results),
        "verdict_counts": {v: sum(1 for r in results if r["verdict"] == v)
                           for v in sorted({r["verdict"] for r in results})},
        "all_expected_matched": all_match,
        "results": results,
        "fail_closed_checks": {
            "non_synthetic_fixtures_refused": True,
            "idea_only_tag_required": True,
            "ledger_required_fields_present": True,
        },
    }
    dry = pkg / "dry_run"
    (dry / "anonymized_packet.json").write_text(json.dumps(packet, indent=1))
    (dry / "blinding_key.json").write_text(json.dumps(key, indent=1))
    (dry / "dry_run_results.json").write_text(json.dumps(out, indent=1))
    (dry / "dry_run_ledger_example.json").write_text(json.dumps(ledger_example, indent=1))
    print(json.dumps({"cards": len(results), "verdict_counts": out["verdict_counts"],
                      "all_expected_matched": all_match}, indent=1))
    return 0 if all_match else 1

if __name__ == "__main__":
    sys.exit(main())
