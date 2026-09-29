#!/usr/bin/env python3
"""Stage B: rebuild the 131-symbol universe.json (rev-6.1 §5B consistency check).

Rule (UNIVERSE.md documented steps):
  1. ADDV ranking -> top-120 cutoff   (from Stage-A recomputed ranking)
  2. new-listing admissions           (from Stage-A recomputed listing eval: 11 admitted)

Rebuilt universe = 120 ranked names + 11 admitted listings = 131 identities.

Inputs (Stage-A outputs only; whitelisted baseline files are check targets,
never reconstruction inputs):
  canonical_stage_a/addv_ranking_recomputed.json        (229 ranked)
  canonical_stage_a/new_listings_eval_recomputed.json   (15 candidates)

The whitelisted canonical_baseline/addv_ranking_20230930.json is used ONLY
for the pre-assertion that the recomputed top-120 identities equal the
documented top-120 (it was already proven 229/229 in Stage A).

The whitelisted canonical_baseline/universe.json (SHA-256 fa21ca55...) is used
ONLY as the identity/metadata check target, AFTER the rebuild.

Outputs:
  canonical_stage_b/universe_rebuilt.json        (131 entries, provenance per symbol)
  canonical_stage_b/stage_b_comparison.json      (identity + metadata comparison)

A material identity mismatch is a FINDING: the script reports it and exits
nonzero; nothing is tuned.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORKTREE = "/home/hatch/workspace/canonical-stage-a"
STAGE_A = os.path.join(WORKTREE, "canonical_stage_a")
BASELINE = "/home/hatch/workspace/quality-flow-scanner-v5/canonical_baseline"
OUT = os.path.join(WORKTREE, "canonical_stage_b")

RANKING_WL_HASH = "a1748bf63e2ca8e03092eb4afa72b0ea533aa3b9b5a626ffa6ec03f2b1ed0e0f"
UNIVERSE_WL_HASH = "fa21ca55724993fab6709ab83fef7f2001e7d7672fa9e24f97beb24066893b16"
OVERLAY_WL_HASH = "ecb124d717918ecffe453a47a5d69b9836f01b93cecf1e76a43829d09ea2c07c"

EXPECTED_ADMITTED = {"ARM", "BMNR", "CRWV", "DRAM", "GEV", "GLXY", "NBIS",
                     "RDDT", "SNDK", "SPCX", "TEM"}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(OUT, exist_ok=True)
    findings = []

    # --- 0. Hash whitelisted ranking (pre-assertion target), verify hash ---
    wl_ranking_path = os.path.join(BASELINE, "addv_ranking_20230930.json")
    h = sha256_file(wl_ranking_path)
    assert h == RANKING_WL_HASH, f"whitelisted ranking hash mismatch: {h}"
    print(f"whitelisted addv_ranking_20230930.json SHA-256 OK: {h[:16]}...")

    # --- 1. Load Stage-A outputs (the only reconstruction inputs) ---
    ranking = json.load(open(os.path.join(STAGE_A, "addv_ranking_recomputed.json")))
    listing_eval = json.load(open(os.path.join(STAGE_A, "new_listings_eval_recomputed.json")))
    assert len(ranking) == 229, f"ranking n={len(ranking)}"
    assert len(listing_eval) == 15, f"listing eval n={len(listing_eval)}"
    ranks = sorted(ranking, key=lambda e: e["rank"])
    assert [e["rank"] for e in ranks] == list(range(1, 230)), "rank sequence broken"

    # --- 2. Pre-assertion: recomputed top-120 == whitelisted top-120 ---
    wl_ranking = json.load(open(wl_ranking_path))
    # whitelisted ranking is rank-ordered by list position (no explicit rank field)
    wl_top120 = [e["symbol"] for e in wl_ranking[:120]]
    rec_top120 = [e["symbol"] for e in ranks[:120]]
    if rec_top120 != wl_top120:
        findings.append("PRE-ASSERTION FAIL: recomputed top-120 identities != whitelisted top-120")
        div = [(a, b) for a, b in zip(rec_top120, wl_top120) if a != b]
        print("PRE-ASSERTION FAIL:", div[:10])
        sys.exit(2)
    print("pre-assertion OK: recomputed top-120 identities == whitelisted top-120")

    # --- 3. Admitted listings from Stage-A eval ---
    admitted = [e for e in listing_eval if e["admitted"]]
    rejected = [e for e in listing_eval if not e["admitted"]]
    admitted_ids = {e["symbol"] for e in admitted}
    assert len(admitted) == 11 and len(rejected) == 4
    if admitted_ids != EXPECTED_ADMITTED:
        findings.append(f"admitted identities != expected: {sorted(admitted_ids)}")
        print("ADMITTED IDENTITY MISMATCH:", sorted(admitted_ids))
        sys.exit(2)
    print(f"admitted 11 identities exact: {sorted(admitted_ids)}")

    # --- 4. Rebuild: 120 ranked + 11 admitted = 131 ---
    top120_ids = set(rec_top120)
    overlap = top120_ids & admitted_ids
    if overlap:
        findings.append(f"overlap between top-120 and admitted listings: {sorted(overlap)}")
    rebuilt_ids = top120_ids | admitted_ids
    assert len(rebuilt_ids) == 131, f"rebuilt n={len(rebuilt_ids)}"

    # --- 5. Per-symbol provenance records ---
    rank_by_sym = {e["symbol"]: e for e in ranks}
    eval_by_sym = {e["symbol"]: e for e in listing_eval}
    rebuilt = []
    for e in ranks[:120]:
        rebuilt.append({
            "symbol": e["symbol"],
            "eligible_from": "2023-10-01",
            "eligible_to": "2026-09-30",
            "reason": "top120_addv_2023-09-30",
            "addv_rank_2023_09_30": e["rank"],
            "addv_usd_per_day": e["addv"],
            "provenance": "stage_a_recomputed_addv_ranking",
        })
    for e in sorted(admitted, key=lambda x: x["symbol"]):
        rebuilt.append({
            "symbol": e["symbol"],
            "eligible_from": e["eligibility_date"],
            "eligible_to": "2026-09-30",
            "reason": "new_listing_passed_liquidity_gate",
            "addv_rank_2023_09_30": None,
            "listing_date": e["first_bar"],
            "trail20d_addv_usd_per_day_at_elig": e["trail20d_addv_usd"],
            "trail20d_addv_gate_usd_per_day": e["gate_usd_per_day"],
            "provenance": "stage_a_recomputed_new_listing_eval",
        })
    rebuilt_path = os.path.join(OUT, "universe_rebuilt.json")
    with open(rebuilt_path, "w") as fh:
        json.dump(rebuilt, fh, indent=1)
    rebuilt_hash = sha256_file(rebuilt_path)
    print(f"rebuilt 131-symbol universe written: SHA-256 {rebuilt_hash}")

    # --- 6. Identity comparison vs whitelisted universe.json (check target) ---
    wl_universe_path = os.path.join(BASELINE, "universe.json")
    hu = sha256_file(wl_universe_path)
    assert hu == UNIVERSE_WL_HASH, f"whitelisted universe.json hash mismatch: {hu}"
    target = json.load(open(wl_universe_path))
    target_ids = {e["symbol"] for e in target}
    assert len(target) == 131 and len(target_ids) == 131

    missing = sorted(rebuilt_ids - target_ids)   # in rebuilt, not in target
    extra = sorted(target_ids - rebuilt_ids)     # in target, not in rebuilt
    identity_match = (not missing) and (not extra)
    print(f"identity comparison: rebuilt={len(rebuilt_ids)} target={len(target_ids)} "
          f"match={identity_match}")
    if missing:
        print("  in rebuilt but NOT in target:", missing)
        findings.append(f"identity divergence (rebuilt-only): {missing}")
    if extra:
        print("  in target but NOT in rebuilt:", extra)
        findings.append(f"identity divergence (target-only): {extra}")

    # --- 7. Metadata field comparison (target-only fields documented) ---
    target_by_sym = {e["symbol"]: e for e in target}
    rebuilt_by_sym = {e["symbol"]: e for e in rebuilt}
    meta_div = []
    max_addv_rel = 0.0
    max_trail_rel = 0.0
    for sym in sorted(rebuilt_ids & target_ids):
        t, r = target_by_sym[sym], rebuilt_by_sym[sym]
        for field in ("reason", "eligible_from", "eligible_to", "addv_rank_2023_09_30", "listing_date"):
            rv, tv = r.get(field), t.get(field)
            if rv != tv:
                meta_div.append({"symbol": sym, "field": field, "rebuilt": rv, "target": tv})
        if r["reason"] == "top120_addv_2023-09-30":
            rel = abs(r["addv_usd_per_day"] - t["addv_usd_per_day"]) / t["addv_usd_per_day"]
            max_addv_rel = max(max_addv_rel, rel)
        else:
            # target rounds trail-20d to 0.1M; compare against that rounding
            rel = abs(r["trail20d_addv_usd_per_day_at_elig"] - t["trail20d_addv_usd_per_day_at_elig"]) \
                / t["trail20d_addv_usd_per_day_at_elig"]
            max_trail_rel = max(max_trail_rel, rel)
    # target-only metadata (not derivable from Stage-A outputs)
    target_only_fields = sorted(
        {k for e in target for k in e.keys()}
        - {k for e in rebuilt for k in e.keys()}
        - {"provenance"}
    )
    print(f"metadata divergences (exact fields): {len(meta_div)}")
    for d in meta_div[:10]:
        print("  ", d)
    print(f"max |rebuilt-target|/target addv_usd_per_day (top-120): {max_addv_rel:.3e}")
    print(f"max |rebuilt-target|/target trail20d (listings):        {max_trail_rel:.3e}")
    print(f"target-only fields (not reconstructible): {target_only_fields}")

    # --- 8. Overlay check ---
    overlay_path = os.path.join(BASELINE, "universe_overlay_14.json")
    ho = sha256_file(overlay_path)
    assert ho == OVERLAY_WL_HASH, f"overlay hash mismatch: {ho}"
    overlay = json.load(open(overlay_path))
    assert len(overlay) == 14
    ov_members = sorted(e["symbol"] for e in overlay if e["in_canonical_universe"])
    ov_outsiders = sorted(e["symbol"] for e in overlay if not e["in_canonical_universe"])
    ov_member_ok = all(s in rebuilt_ids for s in ov_members)
    ov_outsider_ok = all(s not in rebuilt_ids for s in ov_outsiders)
    print(f"overlay: 14 total; {len(ov_members)} members (all in rebuilt: {ov_member_ok}); "
          f"{len(ov_outsiders)} outsiders (all outside rebuilt: {ov_outsider_ok})")
    print(f"  members:   {ov_members}")
    print(f"  outsiders: {ov_outsiders}")
    if not (ov_member_ok and ov_outsider_ok):
        findings.append("overlay membership inconsistent with rebuilt universe")

    comparison = {
        "rule": "top-120 ADDV rank (stage-A recomputed) + 11 admitted listings (stage-A recomputed eval)",
        "whitelisted_input_hashes": {
            "addv_ranking_20230930.json": RANKING_WL_HASH,
            "universe.json": UNIVERSE_WL_HASH,
            "universe_overlay_14.json": OVERLAY_WL_HASH,
        },
        "rebuilt_artifact": "canonical_stage_b/universe_rebuilt.json",
        "rebuilt_sha256": rebuilt_hash,
        "identity": {
            "rebuilt_n": len(rebuilt_ids),
            "target_n": len(target_ids),
            "exact_match": identity_match,
            "rebuilt_only": missing,
            "target_only": extra,
        },
        "metadata": {
            "exact_field_divergences": meta_div,
            "max_addv_rel_dev_top120": max_addv_rel,
            "max_trail20d_rel_dev_listings": max_trail_rel,
            "target_only_fields": target_only_fields,
        },
        "overlay": {
            "n": len(overlay),
            "members": ov_members,
            "members_all_in_rebuilt": ov_member_ok,
            "outsiders": ov_outsiders,
            "outsiders_all_outside_rebuilt": ov_outsider_ok,
            "six_outsiders_claim_holds": len(ov_outsiders) == 6 and ov_outsider_ok,
        },
        "findings": findings,
        "verdict": "PASS" if (identity_match and not findings) else "FINDING",
    }
    with open(os.path.join(OUT, "stage_b_comparison.json"), "w") as fh:
        json.dump(comparison, fh, indent=1)
    print(f"VERDICT: {comparison['verdict']}")
    if findings:
        print("FINDINGS:", findings)
        sys.exit(3)


if __name__ == "__main__":
    main()
