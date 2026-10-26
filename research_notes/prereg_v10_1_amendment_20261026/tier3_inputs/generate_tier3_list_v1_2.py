#!/usr/bin/env python3
"""Tier 3 mechanical symbol selection — generator v1.2 (v1.0.1 amendment).

Implements TIER3_RULE_FROZEN.md v1.0 steps 1–8 with the two amendments
required by the C1 review of preregistration v1.0 (Issue #1 comment
6428626885):

  * Step 6b (NEW, finding 2): issuer-level prior-study exclusion. Step 6
    excluded tickers only, which admitted GOOG — a share class of Alphabet
    Inc., whose Class A (GOOGL) is in UX51. Step 6b removes every candidate
    that is a share class / issuer equivalent of any UX51/X2 issuer, per the
    frozen ISSUER_MAP.json (built by build_issuer_map.py from the archived
    directories by a documented mechanical name-matching rule).
  * Step 8 (finding 1): liquidity is read from the FROZEN S4 aggregate table
    (S4_FROZEN_AGGREGATES.csv) instead of a live Yahoo fetch. The table
    contains only the 12 aggregates the v1.0/v1.1 runs persisted; a candidate
    with no frozen row is ineligible (fail-closed, counted) — the same
    fail-closed treatment the frozen rule gives a symbol whose bars cannot
    be fetched. See INPUTS_AND_GAPS.md for the exact completeness statement.

LOCAL-INPUT-ONLY: this script imports no networking or market-data library
and opens no socket. Every input is a local file whose SHA-256 must match
the pin below; a missing file or a hash mismatch aborts the run (exit 2)
before any selection is computed. Output is a pure function of the pinned
inputs: two runs must be byte-identical.
"""
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "sources"
OUT = HERE / "tier3_list_v1_2.json"

GENERATOR_VERSION = "generate_tier3_list.py v1.2 (v1.0.1 amendment, 2026-10-26)"
RULE_VERSION = ("TIER3_RULE_FROZEN v1.0 (2026-10-26) + v1.0.1 amendment "
                "(step 6b issuer-level exclusion; step 8 frozen S4 table)")
SOURCE_DATE = "2026-10-26"
ADV_CUTOFF = 25_000_000.0
MIN_LAST_CLOSE = 5.00
LIST_SIZE = 12
ADV_WINDOW_BARS = 20

EXPECTED_HASHES = {
    "sources/nasdaqlisted.txt":
        "8e72f822228a2536b0e712e5ee91c14e30db07408cc8863a6d64cb1bac1c2c19",
    "sources/otherlisted.txt":
        "67c1e321790341bf89172e2dc30119e1a39180d3dd4b2d7cb4e420ba02305ca6",
    "sources/nasdaq_screener_raw.json":
        "464e82847212024e3c2b871c487c4ac6a3af854763f82dbd124ed4987b39b912",
    "exclusion_universes.json":
        "c7112909009aa605a380b198d07b3ebd421fa44ce5a4751e830c8496ca535e04",
    "ISSUER_MAP.json":
        "3bccdbf27bbfd0c89810ee16169bdd149b7351a5370995bcd26d7d0d1ad1ed85",
    "S4_FROZEN_AGGREGATES.csv":
        "d345fbabeec144f50f117f4d2a6ae7b947e8acb0a4604af64fa869ed25bbd595",
}

NAME_EXCLUSIONS = [
    re.compile(p, re.IGNORECASE)
    for p in (r"%", r"\bPreferred\b", r"\bPreference\b", r"\bUnits?\b",
              r"\bRights?\b", r"\bWarrants?\b", r"\bNotes?\b")
]
SYMBOL_OK = re.compile(r"^[A-Z]{1,6}$")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_inputs() -> dict:
    """Fail-closed: every pinned input must exist and hash-match."""
    hashes = {}
    for rel, want in EXPECTED_HASHES.items():
        p = HERE / rel
        if not p.is_file():
            print(f"FATAL: pinned input missing: {rel}")
            sys.exit(2)
        got = sha256(p)
        if got != want:
            print(f"FATAL: pinned input hash mismatch: {rel}\n"
                  f"  want {want}\n  got  {got}")
            sys.exit(2)
        hashes[rel] = got
    return hashes


def parse_pipe_file(path: Path):
    rows = []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    header = lines[0].split("|")
    for line in lines[1:]:
        if not line.strip() or line.startswith("File Creation Time"):
            continue
        parts = line.split("|")
        if len(parts) != len(header):
            continue
        rows.append(dict(zip(header, parts)))
    return rows


def main() -> int:
    hashes = verify_inputs()
    stage = {}

    # ---- Steps 1-3: listed, exchange, real security (as v1.1) ---------------
    nas_rows = parse_pipe_file(SRC / "nasdaqlisted.txt")
    oth_rows = parse_pipe_file(SRC / "otherlisted.txt")

    universe = {}  # symbol -> security name
    for r in nas_rows:
        sym = r["Symbol"].strip()
        if r.get("Test Issue") == "N" and r.get("ETF") == "N" and r.get("NextShares") == "N":
            universe[sym] = r["Security Name"]
    stage["s1_nasdaq_real_securities"] = len(universe)
    n_oth = 0
    for r in oth_rows:
        sym = r["NASDAQ Symbol"].strip()
        if r.get("Exchange") in ("N", "A") and r.get("Test Issue") == "N" and r.get("ETF") == "N":
            if sym not in universe:
                universe[sym] = r["Security Name"]
                n_oth += 1
    stage["s2_otherlisted_added"] = n_oth
    stage["after_steps_1_3"] = len(universe)

    # ---- Step 4: common stock only (as v1.1) --------------------------------
    universe = {s: n for s, n in universe.items()
                if not any(p.search(n) for p in NAME_EXCLUSIONS)}
    stage["after_step_4_common_stock"] = len(universe)

    # ---- Step 5: plain ticker (as v1.1) --------------------------------------
    universe = {s: n for s, n in universe.items() if SYMBOL_OK.match(s)}
    stage["after_step_5_plain_ticker"] = len(universe)

    # ---- Step 6: never in any prior study — ticker level (as v1.1) -----------
    excl = json.loads((HERE / "exclusion_universes.json").read_text())
    excluded = set(excl["UX51"]) | set(excl["X2"])
    universe = {s: n for s, n in universe.items() if s not in excluded}
    stage["after_step_6_prior_study_exclusion"] = len(universe)

    # ---- Step 6b: never in any prior study — ISSUER level (v1.0.1) -----------
    issuer_map = json.loads((HERE / "ISSUER_MAP.json").read_text())
    equivalents = set()
    for entry in issuer_map["issuers"].values():
        equivalents.update(entry["equivalent_directory_symbols"])
    removed_6b = sorted(s for s in universe if s in equivalents)
    universe = {s: n for s, n in universe.items() if s not in equivalents}
    stage["step_6b_issuer_excluded_symbols"] = removed_6b
    stage["after_step_6b_issuer_exclusion"] = len(universe)

    # ---- Step 7: listed before the holdout window (IPO year <= 2023) ---------
    screener = json.loads((SRC / "nasdaq_screener_raw.json").read_text())
    ipo_year = {}
    for row in screener["data"]["rows"]:
        y = str(row.get("ipoyear") or "").strip()
        if y.isdigit():
            ipo_year[row["symbol"].strip()] = int(y)
    universe = {s: n for s, n in universe.items()
                if s in ipo_year and ipo_year[s] <= 2023}
    stage["after_step_7_ipo_year"] = len(universe)

    candidates = sorted(universe)
    print("stage counts:", json.dumps(stage, indent=1), flush=True)
    print(f"candidates for liquidity step: {len(candidates)}", flush=True)

    # ---- Step 8: liquidity from the FROZEN S4 aggregate table ----------------
    liquidity = {}  # symbol -> (adv20, last_close, bars_used)
    with open(HERE / "S4_FROZEN_AGGREGATES.csv", newline="") as f:
        for row in csv.DictReader(f):
            liquidity[row["symbol"]] = (float(row["adv20_usd"]),
                                        float(row["last_close_usd"]),
                                        int(row["bars_used"]))
    stage["s8_frozen_table_rows"] = len(liquidity)
    no_row = [s for s in candidates if s not in liquidity]
    stage["s8_candidates_without_frozen_aggregate_fail_closed"] = len(no_row)
    eligible = {s: liquidity[s] for s in candidates
                if s in liquidity
                and liquidity[s][0] >= ADV_CUTOFF
                and liquidity[s][1] >= MIN_LAST_CLOSE
                and liquidity[s][2] >= ADV_WINDOW_BARS}
    stage["after_step_8_liquidity"] = len(eligible)

    # ---- Ranking: ADV20 desc, symbol asc; take top LIST_SIZE ------------------
    ranked = sorted(eligible.items(), key=lambda kv: (-kv[1][0], kv[0]))
    selected = ranked[:LIST_SIZE]

    result = {
        "rule_version": RULE_VERSION,
        "generator_version": GENERATOR_VERSION,
        "source_date": SOURCE_DATE,
        "input_hashes": hashes,
        "parameters": {
            "adv20_cutoff_usd": ADV_CUTOFF,
            "min_last_close_usd": MIN_LAST_CLOSE,
            "list_size": LIST_SIZE,
            "adv_window_bars": ADV_WINDOW_BARS,
            "liquidity_window": "completed sessions 2026-09-01..2026-10-25 (last 20 valid bars) — frozen S4 aggregates, no live fetch",
            "ipo_year_max": 2023,
        },
        "stage_counts": stage,
        "tier3_list": [
            {"rank": i + 1, "symbol": sym, "adv20_usd": adv,
             "last_close_usd": lc, "bars_used": nb}
            for i, (sym, (adv, lc, nb)) in enumerate(selected)
        ],
        "selected_count": len(selected),
        "shortfall_vs_list_size": LIST_SIZE - len(selected),
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=False) + "\n")
    print(f"wrote {OUT} sha256={sha256(OUT)}")
    print("selected:", [e["symbol"] for e in result["tier3_list"]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
