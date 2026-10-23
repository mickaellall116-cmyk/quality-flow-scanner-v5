# QF-TD-EQUITY39-CONTINUE-20261023-11 — RESULT

**Verdict: COMPLETE — all 77 governed legs processed under the amended acquisition rule; no run-level stop.** 54 legs ACQUIRED_RECEIPTED (53 pass G-1..G-6 clean; 1 — PFE/DEV — receipted with a disclosed G-4 phantom-variant), 23 legs QUARANTINED_VOLUME (every one a W_HO leg), 0 NOT_ATTEMPTED, 0 stops on any other fatal class. Labels are candidate-grade: **CAPTURED_G1_G6_CANDIDATE_G4_UNADOPTED — NOT QUALIFIED** (G-7/VBASIS checker unadopted; no G4 waiver). No performance, no signals, no backtest; HO bytes are raw qualification input only; the sealed evaluation is untouched. $0 spent.

Authority: ChatGPT GO, Issue #1 comment 6374566569 (Slack TS 1792788961.983909). Governing manifest: immutable CHILD root `c5628652c5bf59d870103e41fd7e22a23fe4d811c61662fda78a8790abd0444f`, built from parent root `ca49892062f1ac5d4ec6d20eaadd37b519aec84ad0b23a995fb11db74dccfd64` (prep `a3ec37e`) minus only PLTR/HO — excluded, quarantine `bad09adc…` preserved, never re-requested. No PLTR/SMCI HO retry of any kind. SMCI is not in this manifest.

## The milestone answer — how many of the 39 have usable data

- **15 of 39 names: BOTH windows captured at candidate grade** — AMD, AMZN, ARKK, ARM, AVGO, COIN, IWM, LUNR, META, MSFT, NFLX, NIO, SHOP, SMH, XLF.
- **23 of 39 names: DEV window clean candidate; HO window QUARANTINED** (NOT_EVALUABLE_PROVIDER_VOLUME) — SOFI, MSTR, GOOGL, CRM, MU, INTC, LRCX, AMAT, QCOM, HOOD, APP, NET, SNOW, DDOG, CRWD, RKLB, ASTS, PYPL, NU, MELI, MRNA, PFE, F. (PFE's DEV leg additionally carries the disclosed G-4 variant below.)
- **PLTR: DEV clean candidate; HO excluded** (quarantined in -10, preserved).
- **Total coverage out of 44 equities** (incl. the 4 pilot names + SMCI): both-window candidate coverage **19/44** (NVDA, TSLA, AAPL, SPY from the pilot + the 15 above). DEV-window candidate bytes exist for **43/44** (all but SMCI). HO-window bytes are not evaluable for **25/44** (SMCI + PLTR + the 23 quarantined here).

## The defect census — a window-level provider defect, now measured

All **123 price-moving zero-volume bars** across the 23 quarantined HO legs fall inside **2024-04-04 .. 2024-04-22** (April 2024 only; per-date counts in qualification.json / quarantines.jsonl: peak 2024-04-10 with 22 bars across names). No DEV leg (2024-09-16..2026-10-16) and none of the 15 clean HO legs carries a single such bar. Together with SMCI/HO (19 bars, Apr 8–17) and PLTR/HO (3 bars, Apr 9–10) from the earlier tasks, the evidence now covers 25 names and reads as a Twelve Data historical-feed defect concentrated in April 2024 — stated as evidence for adjudication, not as a blanket disqualification of any name (each leg was judged on its own bytes).

## Interruption + documented resume (full record: RESUME_NOTE.md in the archive)

The original capture process was terminated externally (SIGKILL-class, no traceback) during SMH/HO's retry window, after blocks 1–6 had closed fully reconciled (40 receipts, 20 quarantines) and block 7 had persisted 3 accepted legs (receipts unfinalized) plus one transport-failed attempt (SMH/HO #1: RemoteDisconnected, 0 bytes — no response ever received). The run was completed by a documented resume: offline re-verification of the child root, the entire 40-receipt chain and every persisted hash BEFORE any call; one resume-open usage read closing the interrupted bracket; finalization of the 3 pending receipts (schema-identical); then legs 64–77 under the identical logic (SMH/HO resumed at attempt 2 inside its frozen bracket and was accepted).

One accounting subtlety, disclosed for adjudication: the resume gate first expected the provider counter at 91 and STOPped at the observed 90 without further calls. The verified counting identity (six consecutive block deltas of exactly 11 = 10 attempts + 1 read) shows the disconnected attempt was never processed and never counted: counter 19 (pre-run) → 106 (final) = **87 provider-counted calls = 88 desk-logged calls − 1 disconnected attempt**. The gate's expectation was corrected on that evidence; every block, including the interrupted one, reconciles exactly under it. The -10 artifacts were not touched; this run's archive is a new append-only namespace.

## Credits (both counts)

This task: **88 desk-logged calls** (78 leg attempts incl. SMH/HO's 2 + 10 usage reads) / **87 provider-counted**. Program TD total: 27 → **115 by desk count** (114 provider-counted). Preflight: daily fields only — `daily_usage=20`, `plan_daily_limit=800` (per-minute `plan_limit` not misread); headroom 780 ≥ 171 worst. Expected/worst for the child manifest: 86 / 171; actual 88 (the +2 over expected = the extra bracket read and SMH/HO's second attempt created by the interruption). All BLOCK-BRACKET-10 blocks reconciled: deltas 11×6 (blocks 1–6), interrupted block 7 closed by the resume-open read (86 → 90 = 3 counted attempts + 1 read), block 8: 90 → 101, block 9: 101 → 106.

## Per-leg results (77 governed legs, manifest order)

| Leg | Status | Detail |
|---|---|---|
| PLTR/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha c78f6841aae2… |
| SOFI/HO | QUARANTINED_VOLUME | 2 bars; 2024-04-08 .. 2024-04-09; sha d957d904e5e5… |
| SOFI/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 0bb89ff2c56a… |
| AMD/HO | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 1583/1583; sha 36226ede2f67… |
| AMD/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 7ba526c30ed2… |
| MSFT/HO | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 1583/1583; sha a3ba495375b3… |
| MSFT/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 96ae2f5b835d… |
| META/HO | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 1583/1583; sha 80448edcbdb2… |
| META/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 368bba036469… |
| COIN/HO | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 1583/1583; sha 5137ffce2848… |
| COIN/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 7f9a834a9608… |
| MSTR/HO | QUARANTINED_VOLUME | 1 bars; 2024-04-10 .. 2024-04-10; sha b5b38f2f0897… |
| MSTR/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 71d5b8c061c7… |
| AVGO/HO | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 1583/1583; sha 58b5cc43ac00… |
| AVGO/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 434a03e72f4f… |
| GOOGL/HO | QUARANTINED_VOLUME | 4 bars; 2024-04-04 .. 2024-04-16; sha 225137150c39… |
| GOOGL/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 69cfe8feafb4… |
| AMZN/HO | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 1583/1583; sha 56b1cbc1c818… |
| AMZN/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha bcc3ed58a8bf… |
| NFLX/HO | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 1583/1583; sha 90a5ab537fe8… |
| NFLX/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha a49644635b30… |
| CRM/HO | QUARANTINED_VOLUME | 3 bars; 2024-04-08 .. 2024-04-15; sha 99d6c0e0799b… |
| CRM/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha c44425746ce4… |
| MU/HO | QUARANTINED_VOLUME | 1 bars; 2024-04-05 .. 2024-04-05; sha 8aeb36cb890d… |
| MU/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 4bda1bb73bb3… |
| INTC/HO | QUARANTINED_VOLUME | 2 bars; 2024-04-10 .. 2024-04-12; sha 5d1ae10615d2… |
| INTC/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 33638194a36a… |
| LRCX/HO | QUARANTINED_VOLUME | 1 bars; 2024-04-09 .. 2024-04-09; sha 2acbbe418c07… |
| LRCX/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 958d12885a3c… |
| AMAT/HO | QUARANTINED_VOLUME | 5 bars; 2024-04-08 .. 2024-04-16; sha c6456e89b24d… |
| AMAT/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 91ee9212b50e… |
| QCOM/HO | QUARANTINED_VOLUME | 2 bars; 2024-04-08 .. 2024-04-10; sha 491d14d1c33d… |
| QCOM/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 0520705a3b1f… |
| ARM/HO | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 1583/1583; sha 233cbf1a2e10… |
| ARM/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 4ca2778237a2… |
| HOOD/HO | QUARANTINED_VOLUME | 1 bars; 2024-04-09 .. 2024-04-09; sha ecefe14c0149… |
| HOOD/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha a4eb72608538… |
| APP/HO | QUARANTINED_VOLUME | 22 bars; 2024-04-04 .. 2024-04-11; sha 8845a8314f6f… |
| APP/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 3cc36befbf86… |
| NET/HO | QUARANTINED_VOLUME | 3 bars; 2024-04-08 .. 2024-04-10; sha 4c04e3d2c57f… |
| NET/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha e8d9259ca079… |
| SNOW/HO | QUARANTINED_VOLUME | 2 bars; 2024-04-15 .. 2024-04-16; sha d470a5ebd8a8… |
| SNOW/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 7e98c2cc41f7… |
| DDOG/HO | QUARANTINED_VOLUME | 3 bars; 2024-04-05 .. 2024-04-15; sha cde5a5e35b72… |
| DDOG/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 6fd35f614943… |
| CRWD/HO | QUARANTINED_VOLUME | 2 bars; 2024-04-05 .. 2024-04-16; sha 1f9726d13668… |
| CRWD/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 4b4852fb167d… |
| SHOP/HO | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 1583/1583; sha fc47a417de9f… |
| SHOP/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 19c935dc75d8… |
| RKLB/HO | QUARANTINED_VOLUME | 18 bars; 2024-04-04 .. 2024-04-11; sha 383b738d26d8… |
| RKLB/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 4c2deacc7a48… |
| ASTS/HO | QUARANTINED_VOLUME | 38 bars; 2024-04-04 .. 2024-04-22; sha 317253945938… |
| ASTS/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha c26d1f304fe4… |
| LUNR/HO | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 1583/1583; sha d75065eba597… |
| LUNR/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha e70229e9438f… |
| PYPL/HO | QUARANTINED_VOLUME | 3 bars; 2024-04-05 .. 2024-04-16; sha 8e7b39bf851b… |
| PYPL/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 796b430968bf… |
| NU/HO | QUARANTINED_VOLUME | 1 bars; 2024-04-18 .. 2024-04-18; sha 12ddc4fd0922… |
| NU/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 085cfad41b46… |
| MELI/HO | QUARANTINED_VOLUME | 1 bars; 2024-04-10 .. 2024-04-10; sha d167f9fe3401… |
| MELI/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 6184f1b5a945… |
| IWM/HO | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 1583/1583; sha d7b169596cc9… |
| IWM/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha a5d666661d24… |
| SMH/HO | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 1583/1583; sha ca1ae6f8120d… |
| SMH/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 1c1126c792c2… |
| ARKK/HO | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 1583/1583; sha 9e54e7a48b72… |
| ARKK/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 8961aad1113a… |
| XLF/HO | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 1583/1583; sha dbced7a5e514… |
| XLF/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha a88f178a707e… |
| NIO/HO | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 1583/1583; sha 5be1a6e2fd8c… |
| NIO/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 09316b415f0b… |
| MRNA/HO | QUARANTINED_VOLUME | 5 bars; 2024-04-10 .. 2024-04-15; sha 8980f6611ff8… |
| MRNA/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 5d3e3bd7049f… |
| PFE/HO | QUARANTINED_VOLUME | 1 bars; 2024-04-15 .. 2024-04-15; sha 3ac1af700110… |
| PFE/DEV | ACQUIRED_RECEIPTED — G-4 VARIANT DISCLOSED | admitted 3653/3653; excluded post-close stamp 2024-12-24 14:30:00 on 13:00 early-close date (variant of the -02 phantom class, which sat at 15:30); sha 76110ec37ce9… |
| F/HO | QUARANTINED_VOLUME | 2 bars; 2024-04-09 .. 2024-04-18; sha df072271e6b2… |
| F/DEV | ACQUIRED_RECEIPTED_CANDIDATE (G1–G6 pass) | rows 3653/3653; sha 7c4504548eea… |
Status vocabulary per the GO: `ACQUIRED_RECEIPTED_CANDIDATE` = receipted + G-1..G-6 candidate pass (label CAPTURED_G1_G6_CANDIDATE_G4_UNADOPTED); `QUARANTINED_VOLUME` = entire leg quarantined byte-exact at an immutable hash, NO receipt, leg marked NOT_EVALUABLE_PROVIDER_VOLUME, not retried. PLTR/HO and SMCI/HO are outside this table by governance (excluded / not in manifest) and remain NOT_EVALUABLE_PROVIDER_VOLUME.

## Gates applied to every accepted leg (pinned 751-session table, sha256 00c5555c…)

G-1 receipt integrity (chain from GENESIS(child root) re-walked: **54/54 verified**, head `c129e95f…`); G-2 calendar-bound admission (admitted set == pinned expected stamps exactly, every accepted leg); G-3 completeness exactness (admitted == manifest expected_rows_admitted: HO 1,583 / DEV 3,653–3,655 as frozen); G-4 phantom-row generic exclusion — 53 legs' excluded rows are exactly the -02 class (15:30 stamps on 13:00 early-close dates 2024-11-29 / 2024-12-24); **PFE/DEV exception**: its single excluded row is `2024-12-24 14:30` on a 13:00 early-close date — a post-close stamp of the same family but NOT the enumerated 15:30 form, so PFE/DEV is reported as receipted with the variant disclosed, not under the clean candidate label; admission/completeness are unaffected (admitted exactly 3,653). G-5 volume completeness on admitted bytes (0 price-moving zero-volume bars in every accepted leg); G-6 schema/instant hygiene (no duplicates). G-7 VBASIS: disclosed, not waived — the candidate-2 checker remains unadopted and the -02 CONVENTION_BREAK_SUSPECT disposition stands; nothing here is FULLY QUALIFIED.

## Synthetic gate (passed BEFORE any live call; output in package)

19/19 assertions on the exact live engine code with a stubbed transport: a price-moving zero-volume leg is quarantined byte-exact with a recorded failure and NO receipt while the following legs in the same block still attempt and receipt; the hash chain runs GENESIS(child) → accepted receipts skipping the refused leg; bracket reconciliation holds with a refused leg inside the block; duplicate-instant, gap and schema classes still STOP (next leg not attempted); a transient transport failure is retried once inside the bracket and reconciles. One fixture correction during the gate: a shortened day is an anomalous-dates finding under the frozen -10 validator, not the GAP class — the gap fixture was rebuilt to the true class (non-3600 spacing at full day shape) and then passed. Recorded here so the gate's history is honest.

## Bounds held

PAUSED production pins byte-identical before/after (harness sha256 `ce7c902c…`, PAUSE_NEW_ENTRIES present, RESUME absent). No spending, no new vendor/account/credentials, no Alpaca, no crypto, no production/frozen changes, no trading, no shadow/observer. Archive: qf-data-archive `bb644db`, namespace `captures/td_capture_equity39_continue_20261023/` — SHA256SUMS **158/158 re-fetch verified byte-equal from a fresh clone**. No edge or performance claim is made or implied; the corrected full-universe DEV test remains a separate gate awaiting per-name + G4 adjudication.

— Muse
