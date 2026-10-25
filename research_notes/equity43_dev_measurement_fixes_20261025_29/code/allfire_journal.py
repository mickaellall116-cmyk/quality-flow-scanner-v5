"""P7 — All-fire unsuppressed BUY journal (generation / recording layer).

QF-EQUITY43-DEV-MEASUREMENT-FIXES-20261025-29, item P7.

The frozen candidate generation is serialized per symbol: a standalone
trade occupies its symbol until its standalone exit, so the committed
590-candidate ledger contains only NON-OVERLAPPING standalone candidates
— it is not the set of all signal fires (-27 §2.7). This module journals
EVERY completed-bar frozen BUY fire on the generator's evaluation domain
(i in [WARMUP, n-2] per symbol), including fires the serialization
suppressed, and classifies each fire:

  MATCHED_CANDIDATE    the fire opened a standalone candidate (the same
                       (symbol, signal_idx) exists in the candidate set);
                       the caller joins the ledger disposition.
  SUPPRESSED_OVERLAP   the fire occurred while a standalone trade was
                       open on the symbol; generation never evaluated it
                       as a candidate. `occupying_signal_idx` names the
                       standalone candidate that suppressed it.
  GAP_INELIGIBLE_ENTRY the fire was evaluated out-of-trade, but the
                       next-bar entry open was at or below the initial
                       stop threshold (entry <= stop0), so generation
                       skipped it without opening a candidate (the
                       frozen gap rule; DEV total is exactly 1).
  UNCLASSIFIED         none of the above — a fail-closed alarm: the DEV
                       harness asserts the count is zero.

Method: `gen_allfire` mirrors the successor `gen_candidates_censored`
loop statement-for-statement and additionally probes
`pine_buy_signal(df, i)` at every visited bar (the probe is pure; it
cannot alter generation). The harness asserts the mirrored loop's
candidate output is field-identical to the frozen generator's, so the
fire classifications rest on a proven-identical state machine.

Bar-finalization / causal timing: fires are evaluated only on COMPLETED
bars (the frozen signal reads bar i's final OHLC and indicators), and a
fire's earliest actionable instant is the next bar's open — the same
causal contract as the frozen generator. No fire is journaled from an
unfinished bar, and no journal field uses data from after the signal
bar's completion except the entry-eligibility open of bar i+1 (which is
the frozen entry print itself).

The journal is a RECORDING layer beside the candidate ledger. It does
not feed any decision, and it computes no trade outcomes for suppressed
fires.
"""


def gen_allfire(sym, df, pb):
    """Mirror of run_study13.gen_candidates_censored with full probing.

    Returns (fires, trades, censored, skipped_gap) where trades/censored/
    skipped_gap are exactly the mirrored generator's outputs, and fires
    is a list of journal records for every bar where the frozen BUY
    signal fired on the evaluation domain.
    """
    trades, censored, skipped_gap = [], [], 0
    fires = []
    n = len(df)
    i = pb.WARMUP
    in_trade, pos = False, None
    open_sig_idx = None
    while i < n - 1:
        # Probe: pure read of the completed bar i.
        fired = bool(pb.pine_buy_signal(df, i))
        probe = None
        if fired:
            sig = df.iloc[i]
            entry_next = float(df["Open"].iloc[i + 1])
            stop0 = float(sig["Close"] - sig["atr"] * pb.SL_ATR)
            probe = {
                "symbol": sym,
                "signal_idx": i,
                "signal_time": df.index[i].isoformat(),
                "signal_close": float(sig["Close"]),
                "atr": float(sig["atr"]),
                "stop0": stop0,
                "entry_next_open": entry_next,
                "tp1_level": entry_next + float(sig["atr"]) * pb.TP_ATR,
                "_in_trade_at_fire": in_trade,
                "_occupying_signal_idx": open_sig_idx,
                "_became_candidate": False,
            }
            fires.append(probe)
        if not in_trade:
            if fired:
                entry = probe["entry_next_open"]
                stop0 = probe["stop0"]
                if entry <= stop0:
                    skipped_gap += 1
                    i += 1
                    continue
                in_trade = True
                open_sig_idx = i
                probe["_became_candidate"] = True
                pos = {"symbol": sym, "entry": entry, "stop": stop0,
                       "tp1": entry + float(df.iloc[i]["atr"]) * pb.TP_ATR,
                       "tp_hit": False, "runner": stop0,
                       "entry_idx": i + 1, "signal_idx": i,
                       "entry_time": df.index[i + 1]}
                i += 1
                continue
            i += 1
            continue
        bar = df.iloc[i]
        lo, hi, close = float(bar["Low"]), float(bar["High"]), \
            float(bar["Close"])
        if not pos["tp_hit"] and hi >= pos["tp1"]:
            pos["tp_hit"] = True
        if pos["tp_hit"]:
            pos["runner"] = max(pos["runner"],
                                close - float(bar["atr"]) * pb.TRAIL_ATR)
        trend_bear = bar["e21"] < bar["e55"] and close < bar["e200"]
        done = False
        if close < pos["runner"]:
            reason, done = "stop", True
        elif close < bar["e55"] or trend_bear:
            reason, done = ("ema55-bear" if trend_bear else "ema55-break"), \
                True
        if done:
            if i + 1 < n:
                exit_px = float(df["Open"].iloc[i + 1])
                exit_idx, exit_time = i + 1, df.index[i + 1]
            else:
                exit_px, exit_time = close, df.index[i]
                exit_idx = i
            risk_frac = (pos["entry"] - pos["stop"]) / pos["entry"]
            r1 = (pos["tp1"] - pos["entry"]) / pos["entry"] / risk_frac \
                if pos["tp_hit"] else None
            r2 = (exit_px - pos["entry"]) / pos["entry"] / risk_frac
            r_blend = (0.5 * r1 + 0.5 * r2) if r1 is not None else r2
            exit_synth = pos["entry"] * (1 + r_blend * risk_frac)
            trades.append({
                "symbol": sym, "entry": pos["entry"], "stop": pos["stop"],
                "tp1": pos["tp1"], "exit": exit_synth, "reason": reason,
                "tp1_hit": pos["tp_hit"], "entry_time": pos["entry_time"],
                "exit_time": exit_time,
                "hold_bars": exit_idx - pos["entry_idx"],
                "signal_time": df.index[pos["entry_idx"] - 1].isoformat(),
                "signal_idx": pos["signal_idx"]})
            in_trade, pos = False, None
            open_sig_idx = None
        i += 1
    if in_trade and pos is not None:
        censored.append({
            "symbol": sym, "entry": pos["entry"], "stop": pos["stop"],
            "tp1": pos["tp1"], "exit": None,
            "reason": "censored_terminal_open",
            "tp1_hit": pos["tp_hit"], "entry_time": pos["entry_time"],
            "exit_time": None, "hold_bars": None,
            "signal_time": df.index[pos["signal_idx"]].isoformat(),
            "signal_idx": pos["signal_idx"], "censored": True})
    # Classification (precedence: matched > suppressed > gap > alarm).
    for f in fires:
        if f["_became_candidate"]:
            f["classification"] = "MATCHED_CANDIDATE"
            f["occupying_signal_idx"] = None
        elif f["_in_trade_at_fire"]:
            f["classification"] = "SUPPRESSED_OVERLAP"
            f["occupying_signal_idx"] = f["_occupying_signal_idx"]
        elif f["entry_next_open"] <= f["stop0"]:
            f["classification"] = "GAP_INELIGIBLE_ENTRY"
            f["occupying_signal_idx"] = None
        else:
            f["classification"] = "UNCLASSIFIED"
            f["occupying_signal_idx"] = None
        del f["_in_trade_at_fire"], f["_occupying_signal_idx"], \
            f["_became_candidate"]
    return fires, trades, censored, skipped_gap
