# ORB 15m Random-Benchmark — Reproducibility Artifacts Manifest

**Date:** 2026-10-07
**Commit:** e827500 (report)
**Type:** RESEARCH ONLY. No rerun authorized; artifacts are publication of the existing run.

## Test script

- `artifacts/orb_test.py` — standalone script (SHA256: `01416fb90ed16287a08714dc8af95f333d8af21120adc237f388e0d6453f3de7`)
- No frozen-system code touched. Run command (for reference, NOT re-authorized): `python3 /tmp/orb_test.py`

## Input data manifests

| File | SHA256 | Symbol | Venue | Interval | Bars | UTC range (first bar) | UTC range (last bar) |
|---|---|---|---|---|---|---|---|
| `qqq_15m.json` (raw, /tmp) | `71ca5bd4dc11c35dc04aab23c528241cc39b7cf37fe1a9ac0a35573fb5db6050` | QQQ | Tiingo IEX | 15m | 10,000 | 2025-04-17T14:30:00Z | 2026-10-07T18:15:00Z |
| `qqq_15m_early.json` (raw, /tmp) | `203c6e41e9736792bf3686ac6e281d6b55dc96e9ab7c70f14a353ccdd4520023` | QQQ | Tiingo IEX | 15m | 3,718 | 2024-10-01T13:30:00Z | 2025-04-17T19:45:00Z |
| `spy_15m_early.json` (raw, /tmp) | `9f559274c4707c8741e6dd56da59d969cfe238564a0e83bb76b43a0f3f8c5e0d` | SPY | Tiingo IEX | 15m | 3,718 | 2024-10-01T13:30:00Z | 2025-04-17T19:45:00Z |
| `spy_15m_late.json` (raw, /tmp) | `f3d844a4a96124e97896e69ea5795f267fed82857e7ec210a8d4ea5d2ee4eba8` | SPY | Tiingo IEX | 15m | 10,000 | 2025-04-17T14:30:00Z | 2026-10-07T18:15:00Z |

**Provenance:** Tiingo IEX intraday, 15m bars, fetched 2026-10-07 via `custom.tiingo` credential. IEX-exchange prints only, NOT consolidated tape. Prices split-adjusted; dividends not modeled. Combined per symbol ≈ 13,700 bars covering 527 trading days (2024-10-01 → 2026-10-07).

**Note:** raw JSON files live in `/tmp` (ephemeral). Hashes above pin their content as of the run. They were not committed to the repo (size).

## Random seeds

- `SEED = 42` (single seed, `numpy.random.default_rng(42)`)
- `N_RANDOM = 1000` variants per symbol per cost scenario
- Entry bar: `rng.integers(1, n)` uniform over session bars after 09:45
- Direction: `rng.choice([-1, 1])` 50/50
- Same seed used for both QQQ and SPY runs (deterministic, reproducible)

## Per-trade ledger

**UNAVAILABLE.** The run logged aggregate statistics (total R, win rate, avg win/loss, max DD, percentile vs random) but did not persist a per-trade ledger. The script is deterministic given the seed and input data, so a ledger can be regenerated — but no rerun is authorized under the current packaging-only directive.

## 1,000-variant statistics summary (1bp/side, matched-days benchmark)

| Symbol | Random mean | Random median | σ | p5 | p95 | ORB total R | ORB percentile |
|---|---|---|---|---|---|---|---|
| QQQ | −25.0R | −25.6R | 18.6R | −54.3R | +5.4R | +6.0R | 95.4% |
| SPY | −39.5R | −39.5R | 21.3R | −76.0R | −4.5R | +10.8R | 98.9% |

Full per-cost tables in the parent report.

## Timestamp / interval / session handling

- Bars are UTC timestamps from Tiingo; converted to America/New_York (tz-aware, DST-safe).
- Regular session: 09:30–16:00 ET. Range = first 15m bar (09:30–09:45 ET), known at 09:45 ET — no lookahead.
- Entry at the close of the first subsequent 15m bar that closes outside the range.
- Early-close days (day before Thanksgiving, Christmas Eve, July 3rd): traded normally; EOD exit at last bar. All 527 days had a valid 09:30 bar; no exclusions.
- Same-bar stop+target: stop assumed hit first (conservative).
- EOD rule (not in source video): exit at last regular-session bar close if neither stop nor target hit.
