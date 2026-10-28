# P5 — Per-Fill Cost Configuration Package (2026-10-27)

**What this is.** The completion evidence for preregistration v1.0
precondition **P5** (PREREG_V10.md §3 row P5; FREEZE_CHECKLIST_V10.md row
O5): the §8 per-fill cost convention, converted from prose into a recorded,
hashed configuration. P5 was the last freeze-procedure artifact that did
not exist anywhere in the record — the frozen C1 config
(`87b8285a522ba0e3e5a80f0097b9668afc1ddf11da4fc5559c0ca31f55218706`)
records only the flat Stage-1 cost views (gross / 4 bps / 25 bps), as
documented in the G5 package (`MECHANICAL_CHECKS.md`, OPEN_ITEMS row O5).

**Authorization.** Production of this package was authorized by Mike
directly in chat on 2026-10-27 ("I authorized"), resolving the fork
between his G5 adoption text (which carved "P5 execution" out of the
freeze's scope) and the review request to produce it as staging prep.
Scope of that authorization: **authoring this package only.**

**What this package does NOT do.** It opens no tier, runs no performance
test, touches no holdout data, and changes no strategy rule. The config
cannot be used by any run until a future per-tier G7 GO, and the P5 hash
entering the freeze record does not by itself authorize anything. Stage A
additionally still requires the O4 paired SDs (gated on Mike's separate
direct GO) and the per-tier §5 pool counts (staging step) — see the G7
decision package.

## The artifact

| File | Role |
|---|---|
| `per_fill_config.json` | The config. **SHA-256 `7690de07edc3af3eeb977e923c4d0b85e4576a01206705b4a2c30b8f443d69b9`** — this is the hash that enters the freeze record as the P5 completion evidence. |
| `generate_p5_config.py` | Deterministic generator. Offline, stdlib only, declared inputs only (the frozen §7/§8 text encoded as constants with citations). Emits canonical bytes; run twice → byte-identical. |
| `validate_p5_config.py` | Fail-closed validator/verifier. Independently encodes the frozen expectations (does not import the generator): hash equality, exact key sets at every level, PINNED values equal to the frozen text, PROPOSED values internally consistent and still flagged, cross-field arithmetic (per-fill = round-trip / 2). Any deviation exits 1. |
| `test_p5_fixtures.py` | Positive / negative / idempotence fixtures (12 checks; see `FIXTURE_RESULTS.md`). |
| `SHA256_MANIFEST.txt` | SHA-256 of every package file except the manifest itself. |

Verify: `python3 test_p5_fixtures.py` (expect `FIXTURES: 12/12 PASS`), and
`python3 validate_p5_config.py per_fill_config.json --expected-sha256 7690de07edc3af3eeb977e923c4d0b85e4576a01206705b4a2c30b8f443d69b9`.

## Parameters: 14 PINNED, 4 PROPOSED

PINNED — stated in the frozen text (PREREG_V10.md), implemented exactly:

| Parameter | Value | Source |
|---|---|---|
| verdict_round_trip_bps | 25 | §8 para 1 |
| verdict_per_fill_bps | 12.5 | §8 per-fill model |
| sensitivity_round_trip_bps | [4, 10] (sensitivities only, never verdicts) | §8 para 1 |
| fill_cost_formula | cost $ = (bps/10000) × shares filled × fill price | §8 per-fill model |
| net_pnl_formula | Σ exit notionals − entry notional − Σ fill costs | §8 per-fill model |
| net_r_formula | net P&L $ ÷ (shares × (entry − initial stop)) | §8 per-fill model |
| partial_fills | false | §8 Fills |
| fill_price_basis | stated bar open or close | §8 Fills |
| tp1_fill_rule | bar high touches limit | §7 base rule / §8 |
| e1_stop_slippage_atr | 0.05 | §7 arms (E1), §8 Fills; declared assumption [C15] |
| e2_tp1_exceed_margin_atr | 0.05 | §7 arms (E2); declared assumption [C15] |
| hbuy_descriptive_cost_bps | 25 | §8 H-BUY |
| not_modeled | financing, borrow, dividends, taxes | §8 Not modeled |
| cost_currency | USD ("charged in dollars") | §8 per-fill model |

PROPOSED — **not pinned by the frozen text.** Each is encoded explicitly
in the config with `"status": "PROPOSED"` and `"requires_review": true`,
and is an open decision for ChatGPT adjudication and the G7 record. If
adjudication changes any of them, the config changes, its hash changes,
and the superseded hash must never be quoted as the P5 evidence:

1. **sensitivity_per_fill_bps = [2.0, 5.0]** — the per-fill split of the
   4/10 bps sensitivity views, derived by the same halving that maps the
   pinned 25 → 12.5. The frozen text states no per-fill rate for the
   sensitivities. Alternative if rejected: sensitivities computed under a
   different split, or restated as round-trip-only displays.
2. **adjustment_precedence** — order on a single fill: raw fill price →
   arm price adjustments (e.g. E1's 0.05 ATR slippage) → per-fill cost
   computed on the executed price → aggregation. The frozen text states
   slippage as a property of the fill (§7) and cost on "shares filled ×
   fill price" (§8) but never states the composition order. Alternative:
   cost on the pre-slippage price (differs only for E1 stop fills).
3. **rounding_mode = none_full_precision** — dollar costs carried at full
   floating-point precision; the frozen text never addresses rounding.
   Alternative: round each fill's cost to cents.
4. **min_cost_per_fill_applies = false** — no per-fill minimum charge;
   the frozen text contains none. Recorded explicitly so the absence is
   a reviewed fact, not an oversight.

No separate commission, regulatory fee, or spread model exists in the
frozen text; the bps convention is the whole cost model, and none was
invented here.

## Conformance checks (in the fixtures)

The recorded formulas reproduce §8's own worked examples exactly:
exit +10% ⇒ 26.25 bps of entry notional; exit −4% ⇒ 24.5 bps; the 50%
TP1 leg costs 6.25 bps of the full-position notional at the TP1 price
(the §8 equivalence note). Two-stage identity (§8 [C05]): this config is
Stage 2; the Stage-1 ledgers and their parity claims stay under the
predecessor C1 config pin recorded inside the config, and
`claims_carry_across_stages` is false.
