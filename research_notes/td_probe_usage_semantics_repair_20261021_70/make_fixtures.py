#!/usr/bin/env python3
"""Deterministic synthetic fixture builder — task -67 r1.

Writes fixtures/*.json: Twelve-Data-shaped payloads and pilot-shaped
receipts for the NVDA 10:1 (2024-06-10) twin windows. Carries all
-65 variants (uniform scaled volume, vol_unscaled, mixed OHLC,
vol_inconsistent, missing_volume, revision identical/different,
corrupt/wrong-params receipts, decimal-rounding boundary pair) and
the -66 adversarial fixtures (vol_mixed_conventions, swapped
request-ID receipts, duplicate / out-of-order / out-of-window bar
sets, meta symbol/interval mismatches, post-only / pre-only coverage
pairs). ADDS the -67 closure fixtures: byte-identical revision pairs
whose shared snapshot is itself invalid (meta-wrong /
out-of-window / duplicate bars) with base+revision receipts over the
same body, and malformed-numeric snapshots (non-decimal close,
non-decimal volume).

SYNTHETIC ONLY — no vendor bytes. Run once before precommit; outputs
are committed and hashed in SHA256_MANIFEST.txt.
"""

from __future__ import annotations

import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
FIX = HERE / "fixtures"

import probe_analyzer as az  # noqa: E402

NVDA_WIN = ("2023-12-13T00:00:00", "2024-06-21T23:59:59")
BASE_TS_MS = 1_760_000_000_000

NONE_BARS = [
    ("2024-06-07 09:30:00", "1240.00", "1250.00", "1235.00", "1245.00",
     "1000000"),
    ("2024-06-07 10:30:00", "1245.00", "1255.00", "1242.00", "1252.00",
     "1100000"),
    ("2024-06-07 11:30:00", "1252.00", "1258.00", "1248.00", "1255.00",
     "900000"),
    ("2024-06-10 09:30:00", "125.50", "126.50", "124.80", "126.00",
     "12000000"),
    ("2024-06-10 10:30:00", "126.00", "127.00", "125.50", "126.60",
     "11500000"),
]
SPLIT_DATE = "2024-06-10"
FACTOR = Decimal(10)


def _div10(s: str) -> str:
    return str((Decimal(s) / FACTOR).quantize(Decimal("0.01")))


def splits_bars(volume_mode="scaled", mixed=False,
                vol_inconsistent=False, missing_volume=False,
                mixed_conventions=False):
    bars = []
    for i, (dt, o, h, l, c, v) in enumerate(NONE_BARS):
        pre = dt[:10] < SPLIT_DATE
        if pre:
            o, h, l, c = _div10(o), _div10(h), _div10(l), _div10(c)
            if mixed and i == 1:
                c = NONE_BARS[1][4]  # unadjusted close: basis mixing
            if volume_mode == "scaled":
                v = str(int(v) * 10)
            if mixed_conventions and i == 1:
                # this one pre-split bar keeps UNSCALED volume while
                # its neighbours are factor-scaled: both conventions
                # are individually valid -> -65 false PASS case
                v = NONE_BARS[1][5]
            if vol_inconsistent and i == 1:
                v = str(int(NONE_BARS[1][5]) * 5)
        bar = {"datetime": dt, "open": o, "high": h, "low": l,
               "close": c}
        if not missing_volume:
            bar["volume"] = v
        bars.append(bar)
    return bars


def payload(symbol, bars):
    return {"meta": {"symbol": symbol, "interval": "1h",
                     "currency": "USD", "exchange": "NASDAQ",
                     "type": "Common Stock"},
            "values": bars, "status": "ok"}


def none_payload():
    bars = [{"datetime": dt, "open": o, "high": h, "low": l,
             "close": c, "volume": v}
            for dt, o, h, l, c, v in NONE_BARS]
    return payload("NVDA", bars)


def params(symbol, adjust):
    return {"symbol": symbol, "interval": "1h",
            "start_date": NVDA_WIN[0], "end_date": NVDA_WIN[1],
            "timezone": "America/New_York", "outputsize": "5000",
            "order": "ASC", "adjust": adjust}


def write(name, obj) -> bytes:
    raw = json.dumps(obj, indent=1, sort_keys=True).encode()
    (FIX / name).write_bytes(raw)
    return raw


def receipt(request_id, prm, body: bytes, ts_ms: int,
            sha_override=None):
    return {"request_id": request_id, "attempt": 1,
            "request_ts_ms": ts_ms - 1000, "receipt_ts_ms": ts_ms,
            "http_status": 200, "bytes": len(body),
            "sha256": sha_override or hashlib.sha256(body).hexdigest(),
            "headers": {"content-type": "application/json"},
            "params": prm}


def main():
    FIX.mkdir(exist_ok=True)
    none_body = write("nvda_none_uniform.json", none_payload())
    write("nvda_none_uniform.receipt.json",
          receipt("REQ-ADJ-01N", params("NVDA", "none"), none_body,
                  BASE_TS_MS))

    splits_body = write("nvda_splits_uniform.json",
                        payload("NVDA", splits_bars()))
    write("nvda_splits_uniform.receipt.json",
          receipt("REQ-ADJ-01", params("NVDA", "splits"), splits_body,
                  BASE_TS_MS))

    for name, kw in (("vol_unscaled", {"volume_mode": "unscaled"}),
                     ("mixed", {"mixed": True}),
                     ("vol_inconsistent", {"vol_inconsistent": True}),
                     ("missing_volume", {"missing_volume": True})):
        body = write(f"nvda_splits_{name}.json",
                     payload("NVDA", splits_bars(**kw)))
        write(f"nvda_splits_{name}.receipt.json",
              receipt("REQ-ADJ-01", params("NVDA", "splits"), body,
                      BASE_TS_MS))

    # revision pair: identical bytes, later receipt; and one changed
    write("nvda_splits_rev_identical.receipt.json",
          receipt("REQ-ADJ-01R7", params("NVDA", "splits"), splits_body,
                  BASE_TS_MS + 7 * 86_400_000))
    rev_bars = splits_bars()
    rev_bars[3]["close"] = "126.25"
    rev_body = write("nvda_splits_rev_different.json",
                     payload("NVDA", rev_bars))
    write("nvda_splits_rev_different.receipt.json",
          receipt("REQ-ADJ-01R7", params("NVDA", "splits"), rev_body,
                  BASE_TS_MS + 7 * 86_400_000))

    # malformed evidence: corrupt sha; wrong-symbol params
    write("nvda_splits_corrupt.receipt.json",
          receipt("REQ-ADJ-01", params("NVDA", "splits"), splits_body,
                  BASE_TS_MS, sha_override="0" * 64))
    write("nvda_splits_wrongparams.receipt.json",
          receipt("REQ-ADJ-01", params("TSLA", "splits"), splits_body,
                  BASE_TS_MS))

    # --- -66 adversarial fixtures ---------------------------------
    # mixed volume conventions (defect 1): prices uniform, pre-split
    # volume split between factor-scaled and unscaled bars
    mc_body = write("nvda_splits_vol_mixed_conventions.json",
                    payload("NVDA",
                            splits_bars(mixed_conventions=True)))
    write("nvda_splits_vol_mixed_conventions.receipt.json",
          receipt("REQ-ADJ-01", params("NVDA", "splits"), mc_body,
                  BASE_TS_MS))

    # swapped request IDs (defect 2): bodies/params correct, the
    # receipt request_id belongs to the OTHER member of the pair
    write("nvda_splits_swappedid.receipt.json",
          receipt("REQ-ADJ-01N", params("NVDA", "splits"),
                  splits_body, BASE_TS_MS))
    write("nvda_none_swappedid.receipt.json",
          receipt("REQ-ADJ-01", params("NVDA", "none"), none_body,
                  BASE_TS_MS))
    write("nvda_splits_base_revid.receipt.json",
          receipt("REQ-ADJ-01R7", params("NVDA", "splits"),
                  splits_body, BASE_TS_MS))
    write("nvda_splits_rev_baseid.receipt.json",
          receipt("REQ-ADJ-01", params("NVDA", "splits"), rev_body,
                  BASE_TS_MS + 7 * 86_400_000))

    # bar-set defects (defect 2, cont.): duplicate, out-of-order,
    # out-of-window bars on an otherwise uniform splits payload
    uni = splits_bars()
    dup = [uni[0]] + uni
    body = write("nvda_splits_dup_bars.json", payload("NVDA", dup))
    write("nvda_splits_dup_bars.receipt.json",
          receipt("REQ-ADJ-01", params("NVDA", "splits"), body,
                  BASE_TS_MS))
    ooo = [uni[1], uni[0]] + uni[2:]
    body = write("nvda_splits_ooo_bars.json", payload("NVDA", ooo))
    write("nvda_splits_ooo_bars.receipt.json",
          receipt("REQ-ADJ-01", params("NVDA", "splits"), body,
                  BASE_TS_MS))
    oow = uni + [{"datetime": "2024-06-24 09:30:00",
                  "open": "130.00", "high": "131.00",
                  "low": "129.50", "close": "130.50",
                  "volume": "9000000"}]
    body = write("nvda_splits_oow_bars.json", payload("NVDA", oow))
    write("nvda_splits_oow_bars.receipt.json",
          receipt("REQ-ADJ-01", params("NVDA", "splits"), body,
                  BASE_TS_MS))

    # meta mismatches: symbol and interval
    mm = payload("TSLA", splits_bars())
    body = write("nvda_splits_meta_symbol.json", mm)
    write("nvda_splits_meta_symbol.receipt.json",
          receipt("REQ-ADJ-01", params("NVDA", "splits"), body,
                  BASE_TS_MS))
    mi = payload("NVDA", splits_bars())
    mi["meta"]["interval"] = "4h"
    body = write("nvda_splits_meta_interval.json", mi)
    write("nvda_splits_meta_interval.receipt.json",
          receipt("REQ-ADJ-01", params("NVDA", "splits"), body,
                  BASE_TS_MS))

    # coverage pairs: post-only (no pre-split bars) and pre-only
    post_none = [{"datetime": dt, "open": o, "high": h, "low": l,
                  "close": c, "volume": v}
                 for dt, o, h, l, c, v in NONE_BARS[3:]]
    body = write("nvda_none_post_only.json",
                 payload("NVDA", post_none))
    write("nvda_none_post_only.receipt.json",
          receipt("REQ-ADJ-01N", params("NVDA", "none"), body,
                  BASE_TS_MS))
    post_splits = splits_bars()[3:]
    body = write("nvda_splits_post_only.json",
                 payload("NVDA", post_splits))
    write("nvda_splits_post_only.receipt.json",
          receipt("REQ-ADJ-01", params("NVDA", "splits"), body,
                  BASE_TS_MS))
    pre_none = [{"datetime": dt, "open": o, "high": h, "low": l,
                 "close": c, "volume": v}
                for dt, o, h, l, c, v in NONE_BARS[:3]]
    body = write("nvda_none_pre_only.json", payload("NVDA", pre_none))
    write("nvda_none_pre_only.receipt.json",
          receipt("REQ-ADJ-01N", params("NVDA", "none"), body,
                  BASE_TS_MS))
    pre_splits = splits_bars()[:3]
    body = write("nvda_splits_pre_only.json",
                 payload("NVDA", pre_splits))
    write("nvda_splits_pre_only.receipt.json",
          receipt("REQ-ADJ-01", params("NVDA", "splits"), body,
                  BASE_TS_MS))

    # --- -67 closure fixtures --------------------------------------
    # byte-identical revision pairs over an INVALID shared snapshot:
    # base and revision receipts bind the same body (C5 must validate
    # structure BEFORE the identical-bytes PASS branch)
    for stem, bad_payload in (
            ("nvda_splits_revmeta_identical",
             payload("TSLA", splits_bars())),
            ("nvda_splits_revoow_identical", payload("NVDA", oow)),
            ("nvda_splits_revdup_identical", payload("NVDA", dup))):
        body = write(f"{stem}.json", bad_payload)
        write(f"{stem}.base.receipt.json",
              receipt("REQ-ADJ-01", params("NVDA", "splits"), body,
                      BASE_TS_MS))
        write(f"{stem}.rev.receipt.json",
              receipt("REQ-ADJ-01R7", params("NVDA", "splits"), body,
                      BASE_TS_MS + 7 * 86_400_000))

    # malformed numerics: non-decimal close / volume strings
    bad_close = splits_bars()
    bad_close[1]["close"] = "not_a_number"
    body = write("nvda_splits_badnum_close.json",
                 payload("NVDA", bad_close))
    write("nvda_splits_badnum_close.receipt.json",
          receipt("REQ-ADJ-01", params("NVDA", "splits"), body,
                  BASE_TS_MS))
    bad_vol = splits_bars()
    bad_vol[2]["volume"] = "12x34"
    body = write("nvda_splits_badnum_volume.json",
                 payload("NVDA", bad_vol))
    write("nvda_splits_badnum_volume.receipt.json",
          receipt("REQ-ADJ-01", params("NVDA", "splits"), body,
                  BASE_TS_MS))

    # decimal-rounding boundary: search deterministic candidate pairs
    # against the predeclared tolerance (both sides of the boundary).
    found = {}
    s = "100.01"
    cand = Decimal("999.00")
    while cand < Decimal("1002.00") and len(found) < 2:
        n = str(cand.quantize(Decimal("0.01")))
        dev = abs(Decimal(n) / Decimal(s) - FACTOR)
        tol = az.ratio_tolerance(n, s, FACTOR)
        if dev <= tol and "pass_pair" not in found and \
                dev > tol * Decimal("0.5"):
            found["pass_pair"] = {"none": n, "splits": s,
                                  "deviation": str(dev),
                                  "tolerance": str(tol)}
        if dev > tol and "fail_pair" not in found and \
                dev < tol * Decimal("1.5"):
            found["fail_pair"] = {"none": n, "splits": s,
                                  "deviation": str(dev),
                                  "tolerance": str(tol)}
        cand += Decimal("0.01")
    assert len(found) == 2, f"boundary search failed: {found}"
    write("rounding_boundary.json", found)
    print("fixtures written:", len(list(FIX.glob('*.json'))))


if __name__ == "__main__":
    main()
