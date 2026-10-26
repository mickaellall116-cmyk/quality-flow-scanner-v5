#!/bin/bash
# EXP-14B — the single authorized run. Conditional GO: Issue #1 comment 6406229148.
# Readiness PASS: Issue #1 comment 6407503923 (corr2 package 7a0e487).
python3 /home/hatch/workspace/qf_exp14b_run_stage/execution/exp14_buy.py --mode returns \
  --inventory /home/hatch/workspace/qf_decisionb_stage/archive_clone/research_inventory/p7b_20261025/p7b_inventory.jsonl --inventory-sha a6bbd19a702120cafd48cd01ee4c8ff59b838a8bd6439822415d6c18278ef02f \
  --exec-prices /home/hatch/workspace/qf_decisionb_stage/archive_clone/research_inventory/exp14_exec_prices_20261025/exp14_exec_prices.jsonl --exec-prices-sha 4adb8320bd10e8e1e8c650d847290c5a66344b9a21704fba40fc53992af205b8 \
  --cohort /home/hatch/workspace/qf_exp14b_run_stage/research_notes/equity43_dev_buy_decisionb_corr2_20261025/artifacts/exp14_frozen_cohort.json --cohort-sha 35690b806e51eefe388fadf35b04baf5ed4c52f8e30ac193a38cf88246332824 \
  --draws /home/hatch/workspace/qf_exp14b_run_stage/research_notes/equity43_dev_buy_decisionb_corr2_20261025/artifacts/exp14_frozen_draws.json --draws-sha fe54808e282515807703692fb08cf3928ee9a4435d04b6939f2b9f47157e4a8a \
  --out-analysis /home/hatch/workspace/qf_exp14b_run_stage/run_output/exp14b_analysis.json
