#!/usr/bin/env python3
r"""Build the frozen issuer map for the Tier 3 v1.0.1 amendment (C1 finding 2).

Purpose: the v1.0 step-6 exclusion was ticker-only. GOOGL is in the prior
study set (UX51) while GOOG — a different share class of the same issuer,
Alphabet Inc. — was selected at rank 1. This builder derives, for every
issuer in the prior-study set UX51 ∪ X2 (250 symbols, exclusion_universes.json),
the full set of directory symbols that are share classes / issuer equivalents
of that issuer, using ONLY the archived 2026-10-26 NASDAQ Trader directories
(S1/S2). Fully offline: no network access of any kind.

Name-matching rule (mechanical, applied identically to every name):
  issuer_key(name):
    1. lowercase; replace '&' with ' and '; drop every character that is not
       [a-z0-9 ] (removes '.', ',', '-', '/', etc.); collapse whitespace.
    2. remove class/series designators: r'\bclass\s+[a-z0-9]+\b',
       r'\bseries\s+[a-z0-9]+\b'.
    3. remove share-form phrases: 'common stock', 'capital stock',
       'ordinary shares', 'ordinary share', 'american depositary shares',
       'american depositary share', 'depositary shares', 'depositary share',
       then standalone tokens 'shares', 'share', 'stock', 'new'.
    4. strip trailing legal-form tokens repeatedly: inc, corp, corporation,
       company, co, ltd, limited, plc, sa, nv, bv, ag, se, lp, llp, llc.
    5. collapse whitespace; the result is the issuer key.
  Two directory symbols are issuer equivalents iff their issuer keys are
  equal and non-empty.

Symbol notation: exclusion_universes.json uses Yahoo notation ('BRK-B');
the NASDAQ directories use dot notation ('BRK.B'). Directory lookup converts
'-' -> '.'. Equivalents are recorded in directory notation, which is the
notation the Tier 3 generator's candidate universe uses.

Output: ISSUER_MAP.json — a pure function of the archived inputs (sorted
keys, no wall-clock fields), so re-running this builder on the same inputs
reproduces it byte-identically.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "sources"
OUT = HERE / "ISSUER_MAP.json"

LEGAL_SUFFIXES = {"inc", "corp", "corporation", "company", "co", "ltd",
                  "limited", "plc", "sa", "nv", "bv", "ag", "se", "lp",
                  "llp", "llc"}
PHRASES = ["american depositary shares", "american depositary share",
           "depositary shares", "depositary share", "common stock",
           "capital stock", "ordinary shares", "ordinary share"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def issuer_key(name: str) -> str:
    s = name.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\bclass\s+[a-z0-9]+\b", " ", s)
    s = re.sub(r"\bseries\s+[a-z0-9]+\b", " ", s)
    for p in PHRASES:
        s = s.replace(p, " ")
    toks = [t for t in s.split() if t not in ("shares", "share", "stock", "new")]
    while toks and toks[-1] in LEGAL_SUFFIXES:
        toks.pop()
    return " ".join(toks)


def parse_pipe_file(path: Path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    header = lines[0].split("|")
    rows = []
    for line in lines[1:]:
        if not line.strip() or line.startswith("File Creation Time"):
            continue
        parts = line.split("|")
        if len(parts) != len(header):
            continue
        rows.append(dict(zip(header, parts)))
    return rows


def main() -> int:
    # Directory name lookup over ALL rows of both files (any exchange/flag):
    # an issuer equivalent is an equivalent wherever it trades.
    dir_name = {}  # directory symbol -> security name
    for r in parse_pipe_file(SRC / "nasdaqlisted.txt"):
        dir_name[r["Symbol"].strip()] = r["Security Name"]
    for r in parse_pipe_file(SRC / "otherlisted.txt"):
        sym = r["NASDAQ Symbol"].strip()
        if sym not in dir_name:
            dir_name[sym] = r["Security Name"]

    # Screener fallback for names (NASDAQ-listed only), used only if a prior
    # symbol is absent from both directories.
    screener = json.loads((SRC / "nasdaq_screener_raw.json").read_text())
    scr_name = {row["symbol"].strip(): row["name"]
                for row in screener["data"]["rows"]}

    # issuer key -> all directory symbols with that key
    key_to_symbols = {}
    for sym, nm in dir_name.items():
        k = issuer_key(nm)
        if k:
            key_to_symbols.setdefault(k, []).append(sym)
    for k in key_to_symbols:
        key_to_symbols[k].sort()

    excl = json.loads((HERE / "exclusion_universes.json").read_text())
    prior = sorted(set(excl["UX51"]) | set(excl["X2"]))

    issuers = {}
    not_found = []
    multi = []
    for p in prior:
        dir_sym = p.replace("-", ".")
        name = dir_name.get(dir_sym)
        name_source = "directory"
        if name is None:
            name = scr_name.get(p) or scr_name.get(dir_sym)
            name_source = "screener" if name is not None else None
        if name is None:
            not_found.append(p)
            issuers[p] = {"directory_symbol": dir_sym, "directory_name": None,
                          "name_source": None, "issuer_key": None,
                          "equivalent_directory_symbols": []}
            continue
        key = issuer_key(name)
        equiv = key_to_symbols.get(key, []) if key else []
        issuers[p] = {"directory_symbol": dir_sym, "directory_name": name,
                      "name_source": name_source, "issuer_key": key,
                      "equivalent_directory_symbols": equiv}
        if len(equiv) > 1:
            multi.append({"prior_symbol": p, "issuer_key": key,
                          "equivalent_directory_symbols": equiv})

    result = {
        "purpose": ("Frozen issuer map for Tier 3 step 6b (v1.0.1 amendment, "
                    "C1 finding 2): share classes / issuer equivalents of "
                    "every UX51/X2 prior-study issuer, derived mechanically "
                    "from the archived 2026-10-26 NASDAQ Trader directories "
                    "by the name-matching rule in build_issuer_map.py."),
        "source_hashes": {
            "nasdaqlisted.txt": sha256(SRC / "nasdaqlisted.txt"),
            "otherlisted.txt": sha256(SRC / "otherlisted.txt"),
            "nasdaq_screener_raw.json": sha256(SRC / "nasdaq_screener_raw.json"),
            "exclusion_universes.json": sha256(HERE / "exclusion_universes.json"),
        },
        "prior_symbol_count": len(prior),
        "issuers": issuers,
        "multi_class_issuers": multi,
        "prior_symbols_not_in_directories_or_screener": not_found,
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"wrote {OUT} sha256={sha256(OUT)}")
    print(f"prior symbols: {len(prior)}; not found: {not_found}")
    print("multi-class issuers in prior set:")
    for m in multi:
        print(" ", m["prior_symbol"], "->", m["issuer_key"], "->",
              m["equivalent_directory_symbols"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
