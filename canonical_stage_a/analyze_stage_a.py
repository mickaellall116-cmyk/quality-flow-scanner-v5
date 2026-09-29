#!/usr/bin/env python3
"""Stage A — ADDV ranking, new-listing eval, Gate A verdict (rev-6.1, §5A/UNIVERSE.md).

Independent recomputation from the fresh daily cache. Whitelisted artifacts
(addv_ranking_20230930.json, addv_unrankable.json, new_listings_eval.json)
are CHECK TARGETS only — never inputs.
"""
import json, os, hashlib, datetime

WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGE = os.path.join(WORKTREE, "canonical_stage_a")
DATA_DIR = os.path.join(STAGE, "data")
POOL_SRC = "/home/hatch/workspace/quality-flow-scanner-v5/canonical_baseline/candidate_pool.json"

RANK_START, RANK_END = "2023-06-30", "2023-09-30"   # inclusive window
MIN_BARS = 30
NEW_LISTING_GATE_M = 25.0  # $25M/day trailing-20d ADDV
POST_LISTING_TRADING_DAYS = 30

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

def load_cache(symbol):
    fn = symbol.replace("-", "_").replace(".", "_")
    p = os.path.join(DATA_DIR, f"d1_{fn}.json")
    if not os.path.exists(p):
        return None
    return json.load(open(p))

def main():
    pool = json.load(open(POOL_SRC))
    symbols = [e["symbol"] for e in pool]
    assert len(symbols) == 272, f"pool len {len(symbols)}"

    caches = {s: load_cache(s) for s in symbols}
    manifest = json.load(open(os.path.join(STAGE, "fetch_manifest.json")))

    # --- per-symbol window stats ---
    stats = {}
    for s in symbols:
        c = caches[s]
        if c is None or not c["rows"]:
            stats[s] = {"n_total": 0, "first_bar": None, "win_bars": 0, "addv": None}
            continue
        rows = c["rows"]
        win = [r for r in rows if RANK_START <= r[0] <= RANK_END]
        dv = [r[4] * r[6] for r in win]  # close_adj * volume_raw
        stats[s] = {
            "n_total": len(rows),
            "first_bar": rows[0][0],
            "last_bar": rows[-1][0],
            "win_bars": len(win),
            "addv": (sum(dv) / len(dv)) if dv else None,
        }

    # --- exclusion classification (documented rules, UNIVERSE.md) ---
    # ASTX leveraged status: documented in UNIVERSE.md ("ASTX, 2x daily-reset");
    # independently confirmed via yfinance quoteType below (best-effort).
    leveraged = {"ASTX"}
    quote_check = {}
    try:
        import yfinance as yf
        for s in leveraged:
            try:
                qt = yf.Ticker(s).info.get("quoteType")
            except Exception as e:
                qt = f"lookup_failed: {e}"
            quote_check[s] = qt
    except Exception as e:
        quote_check["error"] = str(e)

    def is_crypto(s): return s.endswith("-USD")

    ranking, unrankable = [], []
    new_listing_candidates = []
    for s in symbols:
        st = stats[s]
        reason = None
        if s == "SQ":
            reason = "renamed_XYZ_alias"   # UNIVERSE.md corporate-action table: SQ->XYZ, universe uses XYZ
        elif st["n_total"] == 0:
            reason = "no_daily_data"
        elif is_crypto(s):
            reason = "crypto_pair"
        elif s in leveraged:
            reason = "leveraged_etf"
        elif st["first_bar"] > RANK_END:
            reason = "listed_after_cutoff"
            new_listing_candidates.append(s)
        elif st["win_bars"] < MIN_BARS:
            # thin history inside/around the window (e.g. ARM IPO 2023-09-14)
            if st["first_bar"] >= "2023-06-01":
                new_listing_candidates.append(s)
            reason = f"thin_history_{st['win_bars']}bars"
        if reason:
            unrankable.append({"symbol": s, "reason": reason})
        else:
            ranking.append({"symbol": s, "addv": st["addv"], "win_bars": st["win_bars"],
                            "first_bar": st["first_bar"], "last_bar": st["last_bar"]})
    ranking.sort(key=lambda e: -e["addv"])

    # --- new-listing eval (recomputed from cache) ---
    evals = []
    for s in sorted(new_listing_candidates):
        rows = caches[s]["rows"]
        elig_idx = POST_LISTING_TRADING_DAYS  # 31st bar (0-based index 30)
        if len(rows) <= elig_idx:
            evals.append({"symbol": s, "status": "insufficient_history_for_eligibility",
                          "n_bars": len(rows)})
            continue
        elig_date = rows[elig_idx][0]
        trail = rows[elig_idx - 19:elig_idx + 1]  # 20 trading days ending at eligibility
        t20 = sum(r[4] * r[6] for r in trail) / 20
        admit = t20 >= NEW_LISTING_GATE_M * 1e6
        evals.append({
            "symbol": s,
            "first_bar": rows[0][0],
            "eligibility_date": elig_date,
            "trail20d_addv_usd": t20,
            "trail20d_addv_M": round(t20 / 1e6, 2),
            "gate_usd_per_day": NEW_LISTING_GATE_M * 1e6,
            "admitted": bool(admit),
        })

    # --- write outputs ---
    out_rank = os.path.join(STAGE, "addv_ranking_recomputed.json")
    out_unr = os.path.join(STAGE, "addv_unrankable_recomputed.json")
    out_nl = os.path.join(STAGE, "new_listings_eval_recomputed.json")
    json.dump([{"rank": i + 1, **e} for i, e in enumerate(ranking)], open(out_rank, "w"), indent=1)
    json.dump(sorted(unrankable, key=lambda e: e["symbol"]), open(out_unr, "w"), indent=1)
    json.dump(evals, open(out_nl, "w"), indent=1)

    # --- Gate A verdict ---
    checks = []
    def check(name, ok, detail):
        checks.append({"name": name, "verdict": "PASS" if ok else "FAIL", "detail": detail})

    check("pool_272_exact", len(symbols) == 272, f"pool={len(symbols)}")
    check("rankable_229", len(ranking) == 229, f"rankable={len(ranking)}")
    check("unrankable_43", len(unrankable) == 43, f"unrankable={len(unrankable)}")
    check("rankable_plus_unrankable_272", len(ranking) + len(unrankable) == 272,
          f"{len(ranking)}+{len(unrankable)}={len(ranking)+len(unrankable)}")

    if len(ranking) >= 121:
        r120, r121 = ranking[119], ranking[120]
        check("cutoff_120_identity", r120["symbol"] == "DVN",
              f"#120={r120['symbol']} ${r120['addv']/1e6:.1f}M/day")
        check("cutoff_120_value", abs(r120["addv"] - 375.7e6) / 375.7e6 <= 0.02,
              f"#120 DVN observed ${r120['addv']/1e6:.2f}M vs target $375.7M")
        check("cutoff_121_identity", r121["symbol"] == "DAL",
              f"#121={r121['symbol']} ${r121['addv']/1e6:.1f}M/day")
        check("cutoff_121_value", abs(r121["addv"] - 373.2e6) / 373.2e6 <= 0.02,
              f"#121 DAL observed ${r121['addv']/1e6:.2f}M vs target $373.2M")
    else:
        check("cutoff_identities", False, "ranking too short")

    check("listing_candidates_15", len(new_listing_candidates) == 15,
          f"candidates={len(new_listing_candidates)}: {sorted(new_listing_candidates)}")
    admitted = sorted(e["symbol"] for e in evals if e.get("admitted"))
    rejected = sorted(e["symbol"] for e in evals if "admitted" in e and not e["admitted"])
    exp_admit = sorted(["ARM","BMNR","CRWV","DRAM","GEV","GLXY","NBIS","RDDT","SNDK","SPCX","TEM"])
    exp_reject = sorted(["CORZ","NNE","RBRK","UMAC"])
    check("admitted_11_identities_exact", admitted == exp_admit,
          f"admitted={admitted}")
    check("rejected_4_identities_exact", rejected == exp_reject,
          f"rejected={rejected}")

    verdict = {"gate": "A", "overall": "PASS" if all(c["verdict"] == "PASS" for c in checks) else "FAIL",
               "checks": checks,
               "astx_quoteType_check": quote_check,
               "run_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    json.dump(verdict, open(os.path.join(STAGE, "gate_a_verdict.json"), "w"), indent=1)

    print(json.dumps(verdict, indent=1))
    print("\nTop 5:", [(e["symbol"], round(e["addv"]/1e6,1)) for e in ranking[:5]])
    print("Bottom 5:", [(e["symbol"], round(e["addv"]/1e6,3)) for e in ranking[-5:]])
    print("\nListing eval:")
    for e in evals:
        if "admitted" in e:
            print(f"  {e['symbol']}: first={e['first_bar']} elig={e['eligibility_date']} "
                  f"trail20d=${e['trail20d_addv_M']:.2f}M -> {'ADMIT' if e['admitted'] else 'REJECT'}")

if __name__ == "__main__":
    main()
