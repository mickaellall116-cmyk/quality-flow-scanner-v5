# Freeze Checklist — Preregistration v1.0

Finite checklist for the v1.0 freeze. An item is either **CLOSED** (evidence on record, cited) or **OPEN** (named owner). This checklist accompanies the v1.0 freeze candidate (`PREREG_V10.md`, SHA-256 `29a0477a13e52ff4467193f69df7ef107048a8801f64c61f43de28d40d2850c6`). **Document acceptance is not authority to run**: clearing this checklist freezes a document; every tier opening still needs its own GO from the user (G7).

**v1.0 bootstrap seed (contract `fc17041`: first 8 bytes, big-endian, of the frozen preregistration's SHA-256): `2999475941474119668`** — computed from the final assembled `PREREG_V10.md` bytes above and recorded in `P11_PINS_V10.json`. Any byte change to the document recomputes this value and must be logged as an amendment.

## A. Closed on evidence (carried from v0.3, unchanged)

| # | Item | Evidence |
|---|---|---|
| A1 | Measurement layer P1–P4, P6–P9 PASS (bounded) | Issue #1 comment `6400814802` (closure); packages -29 `2cf06fc`, -29r `70ef367`, -30 `d077532`, -31 `848f75d` |
| A2 | R19 per-cost-view ledgers delivered; 25 bps 185-vs-187 resolved on record | -29 commit `2cf06fc`; comment `6398111535` |
| A3 | P7 all-fire census countable (2,892 = 590 + 2,301 + 1 + 0) | -29 commit `539e0a9`, `allfire_summary.json` |
| A4 | Corrected power arithmetic on record (693 / 1,392 / 3,506 / 1,829 / 8,013 / 4,179) | -28 §1.2 (commit `f625921` state); comment `6394587059` |
| A5 | -28 dispositions fully accounted (WITHDRAWN 9 · REVISED 10 · STANDS 1; N1–N4) | `CHANGELOG_V03.md` register (C01–C25, W01–W09), incorporated by pin |
| A6 | Session calendar qualified + extended through 2027 (union 1,054 sessions) | -30 commit `d077532` (extension sha `d2fa788d…`); base table sha `00c5555c…` |

## B. Closed 2026-10-26 (decisions + completed freeze work)

| # | Item | Evidence |
|---|---|---|
| B1 | **§9 contamination audit run; outcome PARTLY CONTAMINATED (F-A2-1)** — §11 Partly branch operative: Tier 2 supplementary (no PASS/FAIL standing), Stage A verdict legs Tier-3-only. B1 REDUCED adopted as amended | Audit package commit `f7b37cc`; audit doc sha `ebaca6a0…`; decisions of record (Mike + ChatGPT, 2026-10-26). A1 COMPLETE, A3 PASS (158/158 + 13/13, chain 54/54), A4 CLEAN |
| B2 | **§11 contract adopted: ECONOMICS-FIRST** — PASS = gates + θ̂ ≥ δ + L > 0; CONFIRMED AT δ (L ≥ δ) retained as the stronger grade; controls, costs, minimum effects preserved | Decision B2 (Mike + ChatGPT, 2026-10-26), logged as a pre-unblinding amendment; `CHANGELOG_V10.md` `[V02]` |
| B3 | Primary H-BUY horizon: **10 bars** (as drafted) | Preserved through the 2026-10-26 decisions |
| B4 | Feasibility decision: **expand the sample (Tier 3)** | B1 decision; Tier 3 generated (row B7). UNDERPOWERED determinations for the strict grade stand in the power report |
| B5 | Stage design: **A-then-B as drafted** | Preserved through the 2026-10-26 decisions; Stage A/B execution packages assembled (`stage_packages/`) |
| B6 | Per-fill cost convention (§8) **confirmed** as the intended accounting | Decisions of record (costs preserved). The config hash itself is an open freeze-procedure step (row O5) |
| B7 | P10 data-rights / session / adjustment audit — production complete (v0.3 item C2; gate G3) | `P10_AUDIT.md` sha `045281e2…` (this package). Independent review rides with O1 below |
| B8 | P11 immutable version pins — complete, **no UNVERIFIED pin remains** (v0.3 item C3; gate G3) | `P11_PINS_V10.json`: post-erratum `pine_backtest.py` RESOLVED (`262ec034…`, erratum commit `d06dfe3`, parent = P0 pin `874d2a9b…`); v1.0 seed entered (header above) |
| B9 | Power report (§6) published — variance only, both grades powered per endpoint (v0.3 item C4; gate G3) | `POWER_REPORT.md` sha `af8aef64…`. Residue: 7A paired SDs (row O4) |
| B10 | Tier 3 rule + list (v0.3 item C5) | Rule sha `b4b993e8…`; script v1.1 `0b39e1d4…`; list sha `9e7ae052…`; `REPRODUCIBILITY_RECORD.md` — REPRODUCIBLE (runs 1/3/4 byte-identical) |

## C. Open — named owners

| # | Item | Owner | What closing it takes |
|---|---|---|---|
| O1 (= v0.3 C1) | Independent review of the v1.0 package | ChatGPT (reviewer); Muse responds | Review comments on the record; disagreements resolved or escalated to Mike (§15 G1–G2) |
| O2 | **A5 — written human-exposure attestation** (§9 audit gap G1) | **Mike** | Mike's attestation logged with the §9 outcome. Muse's position is attested from the record in the audit; ChatGPT/Claude positions are documented indirectly |
| O3 | **G5 — signed freeze of v1.0** (tag + hash; document locked) | **Mike** | Mike's freeze decision after O1. This package is the freeze candidate; assembly is not the freeze |
| O4 | 7A paired SDs — variance-only estimate entered into the freeze record | Muse | Pooled arm-difference variance on DEV, variance only, no group differences. **Must close before any tier opens** (§6) |
| O5 | P5 per-fill config hash produced and pinned | Muse | Per-fill conversion recorded in the config with its hash (§8 two-stage rule). **Must close before any tier opens** |
| O6 | Per-tier §5 pool counts at staging | Muse | Pool-size counts at the frozen ladder step (c) for the tier being staged, outcome-blind. **At staging, before that tier's GO** |
| O7 | Stage B F2 — feed qualification verdict (pilot) **and** a rights basis for ongoing collection | Adjudication + Mike | Pilot verdict under its own adjudication (finalization Mon 2026-11-02) **plus** a rights basis for ongoing collection: the pilot is strictly feed evaluation under Twelve Data Basic and a successful pilot does **not** authorize ongoing collection on Basic (Mike, 2026-10-26; P10 §1.1) |
| O8 | **G7 — per-tier opening GOs** | **Mike** | A separate explicit GO for each tier opening, in §11 stage order. Not given for any tier |

## D. Standing (never closed by this package)

| # | Item | State |
|---|---|---|
| D1 | Holdout | SEALED until its own access GO (G7) is given |
| D2 | Production | PAUSED |
| D3 | S1 | LAUNCH_HOLD (separate authority; untouched by this package) |
| D4 | G4 / VBASIS | UNADOPTED |
| D5 | Original C1 verdict | FAIL (closed; not reopened by anything in this package) |
| D6 | DEV status | EXPLORATORY — no validated edge is claimed anywhere in v1.0 |
| D7 | Tier 2 standing | SUPPLEMENTARY under the §9 Partly outcome — no PASS/FAIL standing |
