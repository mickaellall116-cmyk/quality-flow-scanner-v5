# Verification Log — Power Report / P10 Audit / P11 Pins

**Date:** 2026-10-26. **Scope discipline:** read-only on `~/workspace/quality-flow-scanner-v5` (git archive / git show extraction into a stage scratch dir; the repo working tree was never modified). No returns or performance figures were computed; no holdout-window data was opened (the audit read package manifests, memos, results metadata and code pins only); no vendor calls; no purchases.

## Direct hash verifications (sha256 recomputed from actual bytes)

| Item | Expected (on record) | Recomputed | Result |
|---|---|---|---|
| Base session table `session_table_751_qualified.json` | 00c5555c… (in -29r/-30 code pins) | `00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f` | MATCH |
| Session extension `session_table_extension_2027.json` | d2fa788d… (-30 artifact + manifest) | `d2fa788d70f2c8677ca49b9e0201940586c051b9227f815b8d2da55b1e5d3a2f` | MATCH |
| All 5 v0.3 package files (draft, changelog, checklist, feasibility, verifier) | `SHA256_MANIFEST.txt` in the package | all five | MATCH (sha256sum -c: 5/5 OK) |
| -13 DEV trade ledger | 267e794c… (cited across -29/-29r/-30) | `267e794c284a409d7d9b6d8e1056c452976b59746062e9e6e18c5664b74c003b` | MATCH |
| v0.2 preregistration PDF (blob at commit 02568b2) | 01c4fff0… (-28 memo, verified there pre-read) | `01c4fff0c94cbf1d48f420b4e71619b7f477b07deaacd76705e9ca788abf00ae` | MATCH |
| EXP-14 corr2 execution code `exp14_buy.py` | corr2 package manifest | `77bd53e82963d65ab743a57f1eff0d23b54467a0e17aaf1831b42e6e96b6f3d8` | MATCH |

## Package manifest checks (sha256sum -c, extracted copies)

| Package | Commit | Files OK / total |
|---|---|---|
| -29 measurement fixes | `2cf06fcab1e033f984cc7cb75df1cee4cf95f210` | 22/22 |
| -29r session-causality repair | `70ef367971bb6895456f875dc0f81fad9e3efbe4` | 12/12 |
| -30 semantic pins + calendar extension | `d0775321bad12bb8739023d8cdd4e82e8bb96405` | 15/15 |
| -31 P6 full-grid exposure | `848f75d62c0556547300c12d818850c85669a5cf` | 5/5 |
| -13 DEV order/censor run | (tree at 2cf06fc) | 6/6 |
| -21 feed-qualification frame | `c2b58d7` | 5/5 |
| EXP-14 succ1 prep | `32dfdb39082b1e6cac54edd257ca20ffca3c4cdf` lineage | 8/8 |
| EXP-14 Decision B corr2 | `7a0e4871e0317c3d9100f8c8f0a49967893bfbb8` | 12/12 |

## Seed verification

- Master seed `7715012043445510037` and bootstrap seed `6050949521315240661`: found as literal pinned constants in the manifest-verified corr2 code (`PINNED_MASTER_SEED` / `PINNED_BOOTSTRAP_SEED`, code/exp14_buy.py), in `artifacts/exp14_feasibility_counts.json` and `artifacts/exp14_frozen_draws.json`, asserted by `verify_package.py`, and identical in the succ1 package (code, artifacts, verifier). Derivation recorded pre-outcome in the succ1 MEMO (first-8-bytes big-endian of SHA-256 of the named strings). **VERIFIED.**
- v1.0 protocol seed: the frozen contract (commit `fc1704128c7961dd6dc1523186afb3c5880e21e2` — resolves in the repo) defines it as the first 8 bytes (BE) of the frozen preregistration's SHA-256. No numeric value exists until the v1.0 document is committed; the rule is pinned in `p11_pins.json`, the value is an at-freeze entry. **Not** substituted with the EXP-14 study seeds.

## Power computations

- All figures in `power_report.md` were computed from the frozen planning constants only (σ = 1.8R; σ_paired = 2.6 ATR; μ_plan = +0.17R; δ = 0.05R / 0.10 ATR / 0.10R; z₀.₉₅ = 1.6449, z₀.₈₀ = 0.8416) using the normal-approximation formulas stated in the report. The reused -28 requirements were spot-recomputed and match (693 / 1,392→1,391 rounding / 3,506 / 1,829 / 8,013 / 4,179).
- EXP-14B's design effect (0.880) and n_eff were read from the committed run output (`exp14b_analysis.json`, sha `d9f4864e88db97d24a94734c4d847105b9fe0a6f7513e1ab9ba003e147b76467` per its run-package manifest) — a variance ratio from a completed DEV exploratory run, quoted as record only.

## Items marked UNVERIFIED / open (never copied blindly)

1. **Post-erratum successor `pine_backtest.py` full sha256** — only the prefix `262ec034…` exists in the -29 memo, and the successor file is not inside the -29 package's code directory, so the full hash cannot be recomputed from accessible packages. Recorded as UNVERIFIED in `p11_pins.json` with the resolution (hash the successor tree at the v1.0 freeze commit). The pre-erratum pin (`874d2a9b…`, full value in -13 results.json P0 pins) is recorded as VERIFIED_AS_RECORDED.
2. **Frozen C1 config pin `87b8285a…`** — recorded in the manifest-verified -13 package (results.json + RESULT.md) and anchored by the P9 parity chain; the config is an embedded driver structure, not a standalone file, so no independent re-hash was possible. VERIFIED_AS_RECORDED.
3. **H-EXIT paired SDs** — not on record anywhere; the power report publishes the formula + planning grid and names the variance-only estimate as a freeze-procedure step before any tier opens.
4. **Private-archive EXP-14 inputs** (P7b inventory, execution prices) — pinned hash constants were read from the verified corr2 code; the private archive itself was not re-fetched (out of scope; no need).

## Environment note

An early bulk extraction to /tmp filled the 512 MB tmpfs and was aborted; all scratch was redone under `~/workspace/qf_prereg_v10_stage/scratch/` with narrow per-package extraction. No impact on the repo or the deliverables.
