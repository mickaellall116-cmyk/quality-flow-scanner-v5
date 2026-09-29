# FROZEN CANDIDATES — written BEFORE touching 2022 data

Bull window (UX51 4H 2024-09-16→2026-09-14, 4bps, event engine):

| scheme        | ret%  | dd%   | calmar | ruin   | P(DD>20%) |
|---------------|-------|-------|--------|--------|-----------|
| S0 fixed 1.00 | 31.27 | 35.97 | 0.869  | 0.0018 | 0.687     |
| S1 fixed 0.50 | 14.32 | 22.80 | 0.628  | 0.0000 | 0.102     |
| S2 fixed 0.75 | 20.39 | 30.97 | 0.658  | 0.0002 | 0.399     |
| S3 fixed 1.25 | 46.03 | 40.51 | 1.136  | 0.0055 | 0.873     |
| S4 dd-gated   | 29.49 | 29.86 | 0.988  | 0.0000 | 0.305     |

R-space sanity check: expectancy R/trade identical across all schemes (0.195R)
— sizing is pure $ scaling. Verified.

Freeze decision:
- CANDIDATE: S4_dd_gated (the challenger — keeps 94% of S0's return with 6.1pp
  less drawdown; Calmar 0.988 vs 0.869; bootstrap agrees on tail risk)
- CANDIDATE: S0_fixed_1.00 (control — must be re-run on 2022 in the same
  framework for a like-for-like comparison)

Rejected:
- S1/S2: lower DD but much lower return and worse Calmar — pure de-leveraging,
  not an improvement.
- S3: higher Calmar but DD 40.5% and 3x the ruin of control — that is leverage,
  not risk management. Rejected on judgment; Mike's problem is drawdown, not
  insufficient return.

2022 validation to follow: both candidates at 4bps and 25bps.
