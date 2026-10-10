# Path-Signature Feasibility Spike — 2026-10-10

**Authorization:** Mike 2026-10-10 ("learn from it for ours"). DIAGNOSTIC ONLY — no strategy, no trading simulation, no vendor calls, no production/frozen/sealed contact.

**Claim under test (video transcript):** every trading rule is a function of the past price path; the path signature (rough-path theory) is a universal basis, so any indicator ≈ weighted sum of signature terms with Markowitz-optimal weights. Caveats admitted in the transcript: expected signature is noisy to estimate; tested on a few ETFs.

## Data pins (local only)

- `v54_forward/lonewolf_cache/d_ANET.pkl`, `d_SPY.pkl`, `d_XLK.pkl` — daily closes, 2026-06-25 → 2026-09-23 (62/63 bars each).
- **Constraint found:** `research_notes/data_inventory_20261004.md` documents 225 1H downloads, but the scratch dir (`data_inventory_scratch_20261004/h1_raw/`) is empty on disk — the three lonewolf series are the only local daily bars. No downloads performed (per task).
- **Deviation:** 60-day trailing windows infeasible (would leave ~0 samples). Used 20-day trailing windows only.

## Method

Truncated signatures via Chen's identity on piecewise-linear paths (numpy, from scratch):
- 1-D path = log-price over trailing 20 closes; orders 1–3 → 1 / 2 / 3 features.
- 2-D path = (time/W, demeaned log-price); orders 1–3 → 2 / 6 / 14 features (combinatorial growth d^k demonstrated).
- Label: forward 20-day log return. Features use closes ≤ T only — PIT-clean by construction.
- Walk-forward: chronological 60/40 split per symbol, pooled (train n=40, test n=30). Ridge, alpha=1.0 (sweep 0.1–1000 reported). Features standardized on train stats.

**Sanity checks (all exact before trusting the code):**
- Level-1 term == trailing log return to 10 decimals. ✓
- Level-2 (1-D) == ret²/2 to 10 decimals. ✓
- Lévy area on 2-D (time, price): up-then-down vs down-then-up synthetic paths (same net return) give −0.05 vs +0.05 — opposite signs, equal magnitude, matching the hand-computed triangle area. ✓ Shape information lives in the cross terms, as theory says.

## Results

| model | nfeat | OOS R² | hit rate | IS R² |
|---|---|---|---|---|
| momentum-only | 1 | 0.032 | 63.3% | 0.063 |
| sig1 (1-D) | 1 | 0.032 | 63.3% | 0.063 |
| sig2 (1-D) | 2 | −2.495 | 46.7% | 0.140 |
| sig3 (1-D) | 3 | −22.982 | 46.7% | 0.218 |
| mom+sig3 | 4 | −24.329 | 46.7% | 0.220 |
| sig2d-o1 | 2 | 0.032 | 63.3% | 0.063 |
| sig2d-o2 | 6 | −1.319 | 46.7% | 0.653 |
| sig2d-o3 | 14 | **0.236** | 66.7% | 0.848 |

Alpha sweep (OOS R²): momentum 0.039/0.032/−0.036/−0.330/−0.522 at α=0.1/1/10/100/1000; sig2d-o3 0.233/0.236/0.108/−0.258/−0.467.
Permutation null (500 shuffles) for sig2d-o3: observed 0.236 vs null mean −5.7, sd 10.5, P(null ≥ obs) = 0.000 — **null is degenerate** (estimator unstable at 14 feats / 40 train samples), so this p-value is not evidence.

## Honest verdict

1. **Theory confirmed mechanically, adds nothing:** order-1 signature IS trailing momentum (identical numbers to 10 decimals of sanity, identical OOS). The video's "your indicator is a weighted sum of signature terms" is true and vacuous at order 1.
2. **1-D higher orders are pure noise:** OOS R² −2.5 → −23 while in-sample R² climbs — textbook overfit. On a 1-D price path there is exactly one term per level and levels 2+ are deterministic functions of the return; they cannot add information, only variance.
3. **2-D order-3 is suggestive but not evidence:** OOS R² 0.236 / 66.7% hit (20/30) survives α=10, but in-sample R² is 0.85 (14 features on 40 train rows), the test set is 30 samples across 3 correlated symbols in a single 2-month window, and the permutation null is degenerate. The cross-terms encode *within-window timing* of returns — plausibly just fitting the shared Aug–Sep 2026 regime all three names lived through. Cannot distinguish from overfit luck at this sample size.
4. **The video's own caveat reproduced in miniature:** "the expected signature is noisy" — with real data and honest walk-forward, the noise dominates everywhere except possibly the timing cross-terms, which need a real sample to judge.

**Bottom line: nothing here clears a bar for follow-up on this evidence.** The spike's value is the verified implementation (sanity checks exact) plus the clean negative 1-D result. The sig2d-o3 flicker is a hypothesis for a future test with real data, not a finding.

## What a real follow-up would need (NOT run)

- A multi-year, multi-symbol qualified daily panel (sealed 4H stays sealed; the 225-symbol 1H scratch is gone — would need re-acquisition, not authorized here).
- Walk-forward with periodic refits, multiplicity control over signature orders/dimensions, and the portfolio stack (ranking, costs ≥25bps, drawdown shape) — per Mike's standing gates, signature features would enter as candidate inputs to the existing validation machinery, never as a shortcut around it.
- PIT audit of the time-augmentation convention and any normalization choices.

**Standing-rule compliance:** timeframe named (20-day trailing / 20-day forward); PIT audit done (trailing-only features, documented); no goalpost movement; negative result preserved as a finding.
