# Mechanical Checks — P5 and §5 Pool Counts (2026-10-26)

Non-performance checks completed during preparation of the G5 freeze
package. No returns, no group differences, and no outcome quantities
were computed; no holdout data was accessed; no vendor calls were made.
Evidence is the committed record only.

## P5 — per-fill config hash: **BLOCKED** (exact ambiguity stated)

**What P5 requires.** Precondition P5 (§3): "Cost model converted to
per-fill (§8) and recorded in the config… Completion evidence remains
the **new per-fill config hash**, produced as a named freeze-procedure
step before any tier opens." Checklist row O5 repeats it: "Per-fill
conversion recorded in the config with its hash (§8 two-stage rule)."

**What was located.** The frozen C1 experiment configuration of record
is the `EXPERIMENT_CONFIG` dict embedded in the -13 DEV driver:

- File: `research_notes/equity43_dev_order_censor_20261023_13/run_study13.py`
  (file SHA-256 `4962e30d8b42124ebc317aab647351521d107b600c01a42905fce4c41ce4b22b`,
  package commit `521980ab8117dd88bfb0ff38bca54a96738d7995`).
- The driver's own canonical hash (its `CONFIG_SHA256` code:
  `sha256(json.dumps(EXPERIMENT_CONFIG, sort_keys=True, separators=(",", ":")))`)
  was **recomputed from the committed source during this check** and
  reproduces the recorded pin exactly:
  `87b8285a522ba0e3e5a80f0097b9668afc1ddf11da4fc5559c0ca31f55218706`
  (also recorded in the package's `results.json`, file SHA-256
  `42b05ce32ce545e95b919692ad3736316f8f42d9f603b1db42005342be413956`,
  at `experiment_config_sha256` and in both P0/P5_run phases).

**Why that does not close P5 — the ambiguity, exactly.** The located
config records `cost_views: ["gross", "4bps", "25bps"]` — the **flat
per-trade** cost convention of the frozen DEV record (Stage 1 under
§8's two-stage identity rule). It contains no per-fill parameters:
nothing in it records the §8 conversion (12.5 bps × shares × fill
price, charged per fill). Two candidate referents for "the config" in
row O5 therefore diverge:

1. The frozen C1 `EXPERIMENT_CONFIG` above — hashable and reproduced,
   but it is the Stage-1 flat-convention config; §8's prohibition bars
   quoting a Stage-1 artifact as covering Stage-2 (per-fill) numbers.
2. The **new per-fill config** §3 P5 names as the completion evidence —
   a config artifact in which the §8 per-fill conversion is recorded.
   **No such artifact exists in the committed record.** A repo-wide
   search found no config recording a per-fill cost model; the only
   standalone files named `experiment_config.json` are the six staging
   bundles in the -19/-22 packages (all byte-identical, file SHA-256
   `911750faf7468b74d6ba47338226dc2d6ae90e249b24d6062055f2915515b6cb`),
   which embed market-data arrays for the staging gate and likewise
   record no per-fill conversion.

Producing referent (2) means **authoring a new config artifact** (and
pinning the Stage-2 restatement it parameterizes) — a production step
the record assigns to the freeze procedure before a tier opens (P9
Stage-2 staging), not a hash of an existing frozen file. This package
does not author it: placing a new, unreviewed config inside the G5
signature package would smuggle an unreviewed artifact into the
frozen set.

**What closes P5:** production of the per-fill config artifact under
the P9 Stage-2 staging procedure, with its SHA-256 pinned in the
freeze record, before any tier opens. Until then P5 is **OPEN /
BLOCKED** as above. The reproduced C1 pin (`87b8285a…`) stands as the
Stage-1 config identity and is carried in `P11_PINS_V10.json`.

## §5 pool counts — recorded where the frozen record allows; one sub-item BLOCKED

Checklist row O6: "Pool-size counts at the frozen ladder step (c) for
the tier being staged, outcome-blind. At staging, before that tier's
GO."

**Recorded now (from the frozen record only — name counts, no price or
performance data):**

| Pool | Count | Basis |
|---|---|---|
| Tier 2 (clean holdout symbols) | **19 names** | §9 audit defect census (outcome-blind: timestamps + `volume==0` + `high>low` predicates only) |
| Tier 3 (residual list, v1.2.1) | **11 names** | BE, ACN, IREN, CRDO, TWLO, AAOI, MPWR, SPOT, BABA, COF, BLK (O9 closed) |
| Stage-A prospective universe | **30 names** | 19 + 11; ≥ the §6 20-symbol validity floor |
| DEV (Tier 1) §5 feasibility, frozen step (c) | **311 de-clustered events; 71 dropped (22.83%); 240 events retained** | §5 status `[V07]` (EXP-14 lineage outcome-blind check; ladder frozen at step (c)) |

**BLOCKED sub-item:** the per-event §5 pool counts for Tier 2 and
Tier 3 (for each signal event, the count of eligible same-symbol pool
bars under rules 1–5 at the frozen step (c)) cannot be produced from
the frozen record. They are computed by running the §5 matching code,
in pool-sizes-only mode, over the **sealed holdout-window bars**;
opening that window for any purpose requires the tier's own access
authority. Per row O6 they are produced **at staging, outcome-blind,
before that tier's G7 GO**. No figure beyond the name counts above is
stated, and none may be inferred from DEV counts.

## Verification reproducibility

`VERIFY_MANIFEST.py` (in this package) recomputes, from the repository
alone: every SHA-256 in `FREEZE_MANIFEST.md`, each package's committed
manifest check, the C1 config canonical pin above, and the Tier 3
canonical array hash. It reads committed blobs via `git show` and
computes no performance quantity.
