# V5.4 Forward-Test Flat-Book Claim — Ledger Pins & Reconciliation

Date of intake: 2026-10-12 (pins read 2026-10-13T02:10Z).
Authorization: Mike, main chat, 2026-10-12 22:07 EDT (approving ChatGPT's evidence-intake package).
Method: READ-ONLY intake. No harness or backtest rerun. No changes to frozen code, state, or ledger files. Working-tree uncommitted harness changes untouched.

## Claim under reconciliation

"21 closed trades, cumulative +13.0547R, 0 open; CRWD +1.6305R blended and OKTA +3.5523R blended, both closed on the 2026-10-12 06:30 ET bar (30-bar max)."

## Verdict: EXACT MATCH

Independent recomputation from the append-only ledger reproduces every element of the claim exactly:

| Claim element | Claimed | Recomputed from ledger | Match |
|---|---|---|---|
| Closed trades | 21 | 21 `close` records (21 unique signal_ids) | ✅ |
| Cumulative R | +13.0547R | 13.0547 (sum of stored `blended_r`, exact at 4dp) | ✅ |
| Open positions | 0 | state.json: 21 positions, all `status=closed`; `pending={}`; `close_logged=21` | ✅ |
| CRWD blended | +1.6305R | +1.6305R (1 close record) | ✅ |
| OKTA blended | +3.5523R | +3.5523R (1 close record) | ✅ |
| CRWD/OKTA close bar | 2026-10-12 06:30 ET, 30-bar max | both `exit_bar=2026-10-12T06:30:00-04:00`, `bars_held=30`, `exit_reason=runner-time`, logged 2026-10-12T14:51:40Z | ✅ |

Cross-check: the harness's own published snapshot `forward_test/v54_status.json` independently states `closed_trades=21`, `cumulative_r=13.0547`, `open_positions=[]`.

### Recomputation detail

- Ledger composition: 458 lines = 30 `signal` + 407 `event` + 21 `close` records.
- The 21 closes: 10 wins / 11 losses by `blended_r` sign. The 10 stop exits record `blended_r = −1.0` with `partial_r`/`runner_r` null (no TP1 taken); the 11 TP1'd trades carry both legs.
- `blended_r` derivation (v54_exit_tracker.py, lines 202–212): full-position exit R when no partial was taken; otherwise `partial_r + 0.5 × runner_r` computed from unrounded legs and stored rounded to 4dp (CRWD check: 0.8284 + 0.5×1.6041 = 1.63045 → 1.6305 ✅; OKTA check: 1.0895 + 0.5×4.9256 = 3.5523 ✅).
- One immaterial rounding note: recomputing RBLX's blended from the ledger's *rounded* legs gives −0.1305 vs the stored −0.1306 (0.0001), because the stored value was computed from unrounded legs. The stored `blended_r` values — the figures the claim is stated in — sum exactly to 13.0547.
- CRWD legs: partial 0.8284 / runner 1.6041, exit_px 267.65. OKTA legs: partial 1.0895 / runner 4.9256, exit_px 230.395.

## Evidence pins (as they exist at intake)

### Ledger
- `v54_forward/forward_test.jsonl`
- SHA-256: `7af698450bbd3f319d7a4320abf7b5a2d4c4bdd368a28ae5f57b627839728624`
- Size: 177,507 bytes; 458 lines. Hash verified identical at start and end of intake (stable — the last appends are the CRWD/OKTA closes at 2026-10-12T14:51:40Z).
- Git state: **untracked on `main`** (the whole `v54_forward/` directory is working-tree-only at HEAD `cb3a30d0ee9f2d25bb5f7111fce2003fb0470dd5`; the V5.4 stack's branch home is `recovery-4h-20261004`).

### State
- `v54_forward/state.json`
- SHA-256: `8bd5711cd7bb5e8fbcbca78c2c156df7f33b874792df0e674e5e4980971d0281` (87,919 bytes)
- Contents at read: `runs=519`, `last_run=2026-10-13T01:51:15Z`, 21 positions all closed, `pending={}`, `close_logged=21`.
- Caveat: state.json is live harness state and its hash will drift as observation cycles continue; the closed-trade record it must stay consistent with is the append-only ledger pinned above.
- Published snapshot: `forward_test/v54_status.json`, SHA-256 `8429d7699057cbb778087662c652902b8939305ae9968b59fe9ae909996998b2`, `as_of 2026-10-13T01:51:15Z`.

### Cohort / universe definition
- Composition (v54_forward_harness.py lines 44–50): `FORWARD_UNIVERSE = UX51 (51) + X2 (199) = 250 symbols`; per-cohort analysis, pooled allowed.
- UX51: `hybrid_exit_test.py` (`UNIVERSE_X`, 51 symbols) — SHA-256 `9140504f6449cafe62e1647ccbacaa384427a56ff111cab8c6e9298a220cf45b`, 12,422 bytes. **Untracked on `main`.**
- X2: `v54_universe_x2.py` (`UNIVERSE_X2`, 199 symbols; header: FROZEN 2026-09-15, "Never edit this list during the forward test") — SHA-256 `44b0d8ba5a7ea6415652fdfa1e89a0f9bb57d191bfb0d66c578f9d7a3f5880c9`. **Untracked on `main`.**

### Grid / config
- Rule set as declared by the harness snapshot: "V5.4 frozen 2026-09-15 (structural + ADX>=20 entries, Mode B exits, A/B/C grading)"; exits per frozen stack: structural stop, 50% at TP1, +1R arms Profit Protect, 30-bar max hold.
- `v54_forward_harness.py` — SHA-256 `11829353123b611818c9eafd36260f95cfd24d3b78157dd09e606a5cb4d1b380`, 67,205 bytes. **Tracked on `main` but the working-tree copy DIFFERS from HEAD** (`f71e8aeb…`) — uncommitted harness modifications exist and were not touched by this intake. The pin above is the working-tree file that actually runs.
- `v54_rules.py` — SHA-256 `1b55dedce3b17b1670ac7ee75bfcf4375a0162a1daa780a8abb4199c9ebb817a`. Untracked on `main`.
- `v54_engine.py` — SHA-256 `bde3288307ac7b9bfbded29af89b056ae849f49d91b51c1151dad860224eb8fb`. Untracked on `main`.
- `v54_exit_tracker.py` (computes `blended_r`) — SHA-256 `3ee92864f1afe98ce543803b8b844c1677a6d0e0ce1a6e61d1b7ea74b329a9e0`. Untracked on `main`.

## Scope statement

This note is **operational reporting reconciliation only**: it verifies that the reported flat-book figures are exactly the figures recorded in the pinned ledger, state, and config artifacts. It is **NOT a performance verdict**, NOT a promotion input, and **NOT a replacement for the corrected-grid −15.23R adverse evidence**, which stands as recorded. The V5.4 standing verdict (closed FAIL, 2026-10-03) is unchanged by this reconciliation.

— Muse (read-only intake, 2026-10-12)
