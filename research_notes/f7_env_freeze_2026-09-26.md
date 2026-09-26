# F7 environment / calendar / timezone freeze — 2026-09-26

**Status: FROZEN for F7 feasibility work. Any change below requires a dated
amendment before any returns are opened. Lab only; no production impact.**

## Runtime

| Item | Frozen value |
|---|---|
| Python | 3.12.3 (main, Aug 31 2026, 10:18:26) [GCC 13.3.0] |
| Platform | Linux-7.0.0-38-generic-x86_64-with-glibc2.39 |
| Timezone database | System zoneinfo (`/usr/share/zoneinfo`); no `tzdata` pip package installed. Freeze check: `America/New_York` on 2026-01-15 must resolve to UTC−05:00 |
| Calendar | NYSE full-session bars: first US equity 4H bar closes 13:30 ET, second closes 16:00 ET; half-days follow the frozen decision-time availability framework (`research_notes/decision_time_availability_audit_amendment_5.md`). Framework status: specification READY, implementation NOT passed — this freeze documents versions only |
| Decision clock | `available_at + frozen_latency_buffer < decision_at` (strict inequality); decision timestamps come from the frozen manifest; no caller-supplied decision-time override |

## Canonical serialization

All F7 artifacts (samples, manifests, packets, reports) serialize as JSON with:
`sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=False`, UTF-8 bytes,
`allow_nan=False` (NaN/Infinity are never serialized — they are UNKNOWN upstream).

## Seeds

| Use | Frozen seed |
|---|---|
| Synthetic adversarial fixtures | 20260926 |
| Missingness placebo (when run) | frozen framework statistic + seed 20260926 (per proposal) |
| Any future randomized split | must be preregistered here before use |

## Hashes (SHA-256, recorded at freeze)

Computed over the exact file bytes committed with this freeze:

- `research_notes/fundamental_data_intake_audit.py`
- `research_notes/fundamental_version_selection.py`
- `research_notes/test_fundamental_data_intake_audit.py`
- `research_notes/test_f7_adversarial_controls.py`
- `research_notes/f7_primary_formulation_frozen_2026-09-26.md` (this spec's sibling)

(Hashes are filled at publish time by the parent agent; the freeze binds the
content, not the hash string. Recompute with `sha256sum` and compare.)

## Verification command

```bash
cd ~/workspace/quality-flow-scanner-v5
python3 -m unittest discover -s research_notes -p 'test_fundamental_data_intake_audit.py'
python3 -m unittest discover -s research_notes -p 'test_f7_adversarial_controls.py'
```

Both suites must pass with zero failures before any further F7 work.
