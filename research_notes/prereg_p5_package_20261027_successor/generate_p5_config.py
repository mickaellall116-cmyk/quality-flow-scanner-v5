#!/usr/bin/env python3
"""Deterministic generator for the P5 per-fill cost configuration.

Produces per_fill_config.json: the artifact whose SHA-256 is the completion
evidence for preregistration v1.0 precondition P5 (PREREG_V10.md section 3,
row P5; FREEZE_CHECKLIST_V10.md row O5). The config records the section 8
per-fill cost convention exactly as frozen.

OFFLINE BY CONSTRUCTION: stdlib only, no network, no vendor calls, no data
files read, no performance quantity computed. Inputs are the frozen text of
PREREG_V10.md sections 7 and 8, encoded below as constants with citations.

Every parameter carries a provenance status:
  PINNED   - the value/rule is stated in the frozen preregistration text
             (citation given).
  PROPOSED - the frozen text does not pin the value; the generator encodes
             an explicit proposal, flagged requires_review, for ChatGPT
             adjudication and the G7 record. Deterministic does not mean
             self-authorized: a PROPOSED value is a decision request, not
             a decision.

Output bytes are canonical: json.dumps(indent=2, sort_keys=True,
ensure_ascii=True) + "\\n". Running the generator twice yields
byte-identical output (verified by test_p5_fixtures.py).

Usage: python3 generate_p5_config.py [output_path]
Prints the SHA-256 of the written file.
"""
import hashlib
import json
import sys

# ---------------------------------------------------------------------------
# Frozen-text constants (PREREG_V10.md). Do not edit without a successor
# preregistration: these constants ARE the section 8 convention.
# ---------------------------------------------------------------------------

PARAMETERS = {
    # Section 8, paragraph 1: "All verdicts use a conservative 25 bps
    # round-trip cost applied per fill".
    "verdict_round_trip_bps": 25,
    # Section 8, per-fill model: "Cost for each fill = 12.5 bps x
    # (shares filled x fill price), charged in dollars at the fill."
    "verdict_per_fill_bps": 12.5,
    # Section 8, paragraph 1: "The 4 and 10 bps results are reported as
    # sensitivities and never decide a verdict."
    "sensitivity_round_trip_bps": [4, 10],
    # PROPOSED (not stated in the frozen text): the per-fill split of the
    # sensitivity views, derived by the same halving that maps the pinned
    # 25 bps round trip to the pinned 12.5 bps per fill.
    "sensitivity_per_fill_bps": [2.0, 5.0],
    # Section 8, per-fill model (formula).
    "fill_cost_formula":
        "cost_dollars = (per_fill_bps / 10000) * shares_filled * fill_price",
    # Section 8, per-fill model: "Trade net P&L in dollars =
    # sum(exit fills) - entry fill - sum(fill costs)".
    "net_pnl_formula":
        "net_pnl_dollars = sum(exit_fill_notionals) - entry_fill_notional"
        " - sum(fill_costs)",
    # Section 8, per-fill model: "net R = that figure divided by risk
    # dollars (shares x (entry - initial stop))".
    "net_r_formula":
        "net_r = net_pnl_dollars / (shares * (entry_price - initial_stop_price))",
    # Section 8, Fills: "no partial-fill assumption".
    "partial_fills": False,
    # Section 8, Fills: "Entries and market exits fill at the stated bar
    # open or close".
    "fill_price_basis": "stated_bar_open_or_close",
    # Section 7 base rule, restated in section 8 (Fills / TP1 assumptions):
    # "The base rule fills TP1 when the bar's high touches the limit."
    "tp1_fill_rule": "bar_high_touches_limit",
    # Section 7 arms table (E1) and section 8 Fills: "E1 stop fills carry
    # 0.05 ATR of slippage on top of the cost model (a declared modelling
    # assumption, section 7)" [C15].
    "e1_stop_slippage_atr": 0.05,
    # Section 7 arms table (E2): "Fills only if the high exceeds TP1 by
    # 0.05 ATR"; declared modelling assumption [C15].
    "e2_tp1_exceed_margin_atr": 0.05,
    # Section 8, H-BUY: "The report adds a descriptive line, signal excess
    # minus 25 bps".
    "hbuy_descriptive_cost_bps": 25,
    # PROPOSED (not stated in the frozen text): the order in which price
    # adjustments and cost computation compose on a single fill. The frozen
    # text states that E1 slippage is a property of the fill ("fill at
    # min(open, stop) with 0.05 ATR extra slippage", section 7) and that
    # cost is charged on "shares filled x fill price" (section 8); the
    # proposal reads "fill price" as the executed (post-adjustment) price.
    "adjustment_precedence": [
        "determine_raw_fill_price",
        "apply_arm_price_adjustments",
        "compute_per_fill_cost_on_executed_price",
        "aggregate_net_pnl_and_r",
    ],
    # PROPOSED (not stated in the frozen text): dollar costs are carried
    # at full floating-point precision; no rounding to cents at any step.
    "rounding_mode": "none_full_precision",
    # PROPOSED (not stated in the frozen text): the convention has no
    # per-fill minimum charge; a fill's cost is exactly the formula value.
    "min_cost_per_fill_applies": False,
    # Section 8, Not modeled: "Financing, borrow, dividends and taxes."
    "not_modeled": ["financing", "borrow", "dividends", "taxes"],
    # Section 8, per-fill model: costs are "charged in dollars".
    "cost_currency": "USD",
}

PROVENANCE = {
    "verdict_round_trip_bps": {
        "status": "PINNED",
        "citation": "PREREG_V10.md S8 para 1: 25 bps round-trip, verdicts",
    },
    "verdict_per_fill_bps": {
        "status": "PINNED",
        "citation": "PREREG_V10.md S8 per-fill model: 12.5 bps x shares x price",
    },
    "sensitivity_round_trip_bps": {
        "status": "PINNED",
        "citation": "PREREG_V10.md S8 para 1: 4 and 10 bps, sensitivities only",
    },
    "sensitivity_per_fill_bps": {
        "status": "PROPOSED",
        "requires_review": True,
        "derivation": "round_trip_bps / 2, extending the pinned 25 -> 12.5 "
                      "halving of S8 to the sensitivity views; the frozen "
                      "text states no per-fill rate for 4/10 bps",
    },
    "fill_cost_formula": {
        "status": "PINNED",
        "citation": "PREREG_V10.md S8 per-fill model",
    },
    "net_pnl_formula": {
        "status": "PINNED",
        "citation": "PREREG_V10.md S8 per-fill model",
    },
    "net_r_formula": {
        "status": "PINNED",
        "citation": "PREREG_V10.md S8 per-fill model",
    },
    "partial_fills": {
        "status": "PINNED",
        "citation": "PREREG_V10.md S8 Fills: no partial-fill assumption",
    },
    "fill_price_basis": {
        "status": "PINNED",
        "citation": "PREREG_V10.md S8 Fills: stated bar open or close",
    },
    "tp1_fill_rule": {
        "status": "PINNED",
        "citation": "PREREG_V10.md S7 base rule / S8 TP1 assumptions: "
                    "fills when the bar's high touches the limit",
    },
    "e1_stop_slippage_atr": {
        "status": "PINNED",
        "citation": "PREREG_V10.md S7 arms table (E1) + S8 Fills; declared "
                    "modelling assumption [C15]",
    },
    "e2_tp1_exceed_margin_atr": {
        "status": "PINNED",
        "citation": "PREREG_V10.md S7 arms table (E2); declared modelling "
                    "assumption [C15]",
    },
    "hbuy_descriptive_cost_bps": {
        "status": "PINNED",
        "citation": "PREREG_V10.md S8 H-BUY: descriptive line, excess - 25 bps",
    },
    "adjustment_precedence": {
        "status": "PROPOSED",
        "requires_review": True,
        "derivation": "composition order is not stated in the frozen text; "
                      "proposal applies arm price adjustments (S7) to the "
                      "fill price before the S8 per-fill cost is computed "
                      "on that executed price",
    },
    "rounding_mode": {
        "status": "PROPOSED",
        "requires_review": True,
        "derivation": "rounding is not addressed in the frozen text; "
                      "proposal carries dollar costs at full precision",
    },
    "min_cost_per_fill_applies": {
        "status": "PROPOSED",
        "requires_review": True,
        "derivation": "no minimum charge appears in the frozen text; "
                      "proposal records that absence explicitly",
    },
    "not_modeled": {
        "status": "PINNED",
        "citation": "PREREG_V10.md S8 Not modeled",
    },
    "cost_currency": {
        "status": "PINNED",
        "citation": "PREREG_V10.md S8 per-fill model: charged in dollars",
    },
}

CONFIG = {
    "artifact": "QF-PREREG-V10-P5-PER-FILL-CONFIG",
    "schema_version": 1,
    # Section 8 two-stage identity rule [C05]: this config is the Stage 2
    # convention. Stage 1 numbers stay under the predecessor config below;
    # no claim carries across stages.
    "stage": 2,
    "protocol": "prereg_v10_20261026",
    "parameters": PARAMETERS,
    "provenance": PROVENANCE,
    "predecessor": {
        # Frozen C1 config (EXPERIMENT_CONFIG in the -13 driver): records
        # only the flat Stage-1 cost views; see G5 package
        # MECHANICAL_CHECKS.md / OPEN_ITEMS_CHECKLIST.md row O5.
        "stage1_config_pin":
            "87b8285a522ba0e3e5a80f0097b9668afc1ddf11da4fc5559c0ca31f55218706",
        "stage1_cost_views_flat": ["gross", "4bps", "25bps"],
        "claims_carry_across_stages": False,
    },
}


def canonical_bytes(config):
    text = json.dumps(config, indent=2, sort_keys=True, ensure_ascii=True)
    return (text + "\n").encode("utf-8")


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "per_fill_config.json"
    data = canonical_bytes(CONFIG)
    with open(out_path, "wb") as fh:
        fh.write(data)
    print(hashlib.sha256(data).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
