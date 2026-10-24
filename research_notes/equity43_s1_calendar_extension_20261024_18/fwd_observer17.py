"""EQUITY43-CORRECTED-FWD-v1 — candidate forward observer (research-only).

QF-EQUITY43-CORRECTED-FORWARD-PARITY-BUILD-20261023-15.

An isolated, OFFLINE candidate implementation of the corrected Quality Flow
forward observer for the exact 43-equity -13 W_DEV universe. It consumes 1h
bars as a forward feed would deliver them (one bar at a time, in arrival
order), builds corrected session-anchored 4H bars (09:30->13:30 and
13:30->16:00 ET wall bins; 09:30->13:00 on 13:00 early closes) ONLY from
complete sessions, emits bars only at bin close (decisions only after bar
CLOSE), and generates candidates with the successor terminal-censoring
semantics of QF-EQUITY43-DEV-ORDER-CENSOR-20261023-13 (package 521980a).

Strategy semantics are NOT re-implemented here: signal/exit primitives,
indicators, ranking features and the portfolio simulators are the pinned
-13 successor engine sources (sha256-pinned in the task contract); this
module is the observer/parity layer only — feed hygiene, bar construction,
streaming candidate state machine, journaling, sentinel gate, restart state.

Fail-closed feed policy (mirrors the -10/-11 capture admission rules):
  * a 1h stamp is accepted iff it belongs to the pinned session table's
    expected hourly start set for its date ([09:30, close) on the hour);
  * post-close stamps on a pinned session date (the 15:30 phantom class)
    are EXCLUDED (journaled, never admitted);
  * pre-open / off-hour / unknown-session stamps are REJECTED;
  * duplicate or out-of-order stamps are REJECTED (no state change);
  * price-moving zero-volume bars, non-finite or non-positive prices and
    negative volume POISON the symbol feed (whole-leg quarantine class:
    the symbol emits no bars and no candidates, other symbols unaffected);
  * a session that finalizes with any expected hour missing is INCOMPLETE:
    no 4H bars are emitted for that date, ever; bars arriving for an
    already-finalized date are REJECTED as LATE_BAR (no backfill, no
    retroactive signals).

The journal is append-only and hash-chained; every completed session
writes an anchor record to a SEPARATE anchor store (a different path from
the journal), so tampering with the journal after the fact is detectable
against an anchor the journal writer does not own. Journal records carry
market time and sequence numbers only (no wall clock), so two executions
over the same feed produce byte-identical journals.

QF-EQUITY43-S1-CAUSALITY-GUARDS-20261023-17 — research-only FORK of the
-16 observer (which carries the -16 TP1-blended exit repair verbatim).
Strategy sources, candidate semantics and frozen pins are UNCHANGED.
Two observer-layer defects found by the -16 adjudication are fixed here:

  * CAUSAL BIN-CLOSE EMISSION. The -15/-16 feed finalized a session only
    when the NEXT session's first admitted bar arrived (or at flush()),
    so a 09:30->13:30 bar was not available at 13:30. Here a bin is
    finalized at strictly-known full-bin completion: the moment its last
    member hour is admitted, the BAR event is emitted with
    emitted_at == bin close == decision_instant, using only data whose
    stamps precede the bin close. Gap semantics are per-bin fail-closed:
    a bin with a missing member fails the session at the moment its
    close provably passes (a stamp at or beyond the bin end is admitted
    — the missing member could now only arrive out-of-order and be
    rejected), at a post-close seal, or at the backstop
    (SESSION_INCOMPLETE, no bars for the uncompleted bins, no
    after-the-fact backfill). A bin completed
    BEFORE a later same-session gap is discovered stands — its
    completeness was strictly known at its close; this is the honest
    prospective semantic and differs from the batch session-atomic rule
    only for sessions that gap mid-session (unknowable earlier). A
    session truncated by an outage is sealed incomplete by the next
    session's first bar (the pre-existing backstop) — never by waiting
    for flush(); flush() remains only the offline end-of-stream
    backstop + terminal censoring, exactly as in -15/-16.
  * JOURNAL-ONLY REPLAY. The -15/-16 journal excluded the BAR payload
    and never journaled accepted raw rows, so no decision could be
    reconstructed from the journal alone. Here EVERY ingested raw row
    is journaled first as an INPUT record (canonical payload, hash-
    chained) and every BAR event journals its full bar payload, so the
    complete run — inputs interleaved with the terminal flush() points
    (SEALED records) — replays byte-identically from the journal alone
    (see replay_journal). This preserves data licensing: the journal is
    the observer's own record of what it consumed, held under the same
    terms as the source receipts; no new acquisition is implied.
"""
import hashlib
import json
import os

import pandas as pd

ET = "America/New_York"
CONTRACT_ID = "EQUITY43-CORRECTED-FWD-v1"

# rejection / event classes
REJ_SCHEMA = "SCHEMA"
REJ_OFF_GRID = "OFF_GRID"
REJ_UNKNOWN_SESSION = "UNKNOWN_SESSION"
REJ_DUPLICATE = "DUPLICATE"
REJ_OUT_OF_ORDER = "OUT_OF_ORDER"
REJ_LATE_BAR = "LATE_BAR"
POISON_VOLUME = "POISON_PRICE_MOVING_ZERO_VOLUME"
POISON_VALUE = "POISON_NONFINITE_OR_NONPOSITIVE"


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      default=str)


def _sha(obj):
    return hashlib.sha256(_canon(obj).encode()).hexdigest()


# ---------------------------------------------------------------- journal
class Journal:
    """Append-only, hash-chained event journal with an external anchor."""

    GENESIS = "GENESIS:" + CONTRACT_ID

    def __init__(self, journal_path, anchor_path):
        self.journal_path = journal_path
        self.anchor_path = anchor_path
        self.records = []
        self.head = self.GENESIS
        self._fh = open(journal_path, "w")

    def append(self, etype, market_time, payload):
        rec = {"seq": len(self.records), "type": etype,
               "market_time": str(market_time), "payload": payload,
               "prev": self.head}
        rec["hash"] = _sha({k: rec[k] for k in
                            ("seq", "type", "market_time", "payload",
                             "prev")})
        self.head = rec["hash"]
        self.records.append(rec)
        self._fh.write(_canon(rec) + "\n")
        self._fh.flush()
        return rec

    def anchor(self, note):
        """Write the current head to the EXTERNAL anchor store."""
        with open(self.journal_path, "rb") as f:
            file_sha = hashlib.sha256(f.read()).hexdigest()
        anchor = {"contract": CONTRACT_ID, "seq": len(self.records) - 1,
                  "head": self.head, "journal_file_sha256": file_sha,
                  "note": note}
        with open(self.anchor_path, "w") as f:
            f.write(_canon(anchor) + "\n")
        return anchor

    def close(self):
        self._fh.close()

    @classmethod
    def resume(cls, journal_path, anchor_path):
        """Reopen an existing journal for append after a restart. The
        chain and the external anchor are verified BEFORE any new record
        is accepted; a divergent journal is refused, never repaired."""
        ok, info = cls.verify(journal_path, anchor_path)
        if not ok:
            raise ValueError(f"journal verification failed on resume: "
                             f"{info}")
        j = cls.__new__(cls)
        j.journal_path, j.anchor_path = journal_path, anchor_path
        j.records = []
        j.head = cls.GENESIS
        with open(journal_path) as f:
            for ln in f.read().splitlines():
                rec = json.loads(ln)
                j.records.append(rec)
                j.head = rec["hash"]
        j._fh = open(journal_path, "a")
        return j

    @staticmethod
    def verify(journal_path, anchor_path):
        """Return (ok, info). Detects record tampering, truncation and
        anchor mismatch. The anchor lives outside the journal file."""
        prev = Journal.GENESIS
        n = 0
        with open(journal_path) as f:
            lines = f.read().splitlines()
        for ln in lines:
            rec = json.loads(ln)
            want = _sha({k: rec[k] for k in
                         ("seq", "type", "market_time", "payload", "prev")})
            if rec["prev"] != prev or rec["hash"] != want \
                    or rec["seq"] != n:
                return False, {"first_bad_seq": n,
                               "reason": "chain break / record tampered"}
            prev = rec["hash"]
            n += 1
        with open(journal_path, "rb") as f:
            file_sha = hashlib.sha256(f.read()).hexdigest()
        with open(anchor_path) as f:
            anchor = json.loads(f.read())
        if anchor["head"] != prev or anchor["seq"] != n - 1 \
                or anchor["journal_file_sha256"] != file_sha:
            return False, {"reason": "anchor mismatch (journal rewritten "
                                     "or truncated after anchoring)",
                           "anchor_seq": anchor["seq"], "records": n}
        return True, {"records": n, "head": prev}


# ------------------------------------------------------------ session table
class SessionTable:
    def __init__(self, table):
        self.sessions = {s["date"]: s for s in table["sessions"]}

    @staticmethod
    def _mins(hhmm):
        h, m = map(int, hhmm.split(":"))
        return h * 60 + m

    def is_session(self, date):
        return date in self.sessions

    def close(self, date):
        return self.sessions[date]["close"]

    def expected_starts(self, date):
        """Hourly bar-open stamps in [09:30, close) — the pinned set."""
        close = self._mins(self.close(date))
        out, mins = [], 9 * 60 + 30
        while mins < close:
            out.append(f"{mins // 60:02d}:{mins % 60:02d}")
            mins += 60
        return out

    def bins(self, date):
        """Corrected 4H wall bins: [(start, end, [hour starts])].
        Full session: [09:30,13:30) + [13:30,close). Early close at or
        before 13:30: a single [09:30, close) bin."""
        close = self.close(date)
        starts = self.expected_starts(date)
        if self._mins(close) <= 13 * 60 + 30:
            return [("09:30", close, starts)]
        b1 = [s for s in starts if s < "13:30"]
        b2 = [s for s in starts if s >= "13:30"]
        return [("09:30", "13:30", b1), ("13:30", close, b2)]


# --------------------------------------------------------------- symbol feed
class SymbolFeed:
    """Streaming 1h feed for one symbol with fail-closed admission."""

    def __init__(self, symbol, table):
        self.symbol = symbol
        self.table = table
        self.accepted = {}        # date -> {hhmm: row dict}
        self.finalized = {}       # date -> True (complete) / False (gap)
        self.emitted_bins = {}    # date -> set of emitted bin indexes
        self.poison = None        # (class, detail)
        self.last_stamp = None    # (date, hhmm) of last processed bar
        self.seen_stamps = set()  # (date, hhmm) ever processed

    # -- helpers
    def _reject(self, cls, stamp, detail):
        return {"type": "REJECTED", "symbol": self.symbol, "class": cls,
                "stamp": stamp, "detail": detail}

    def ingest(self, row):
        """Process one raw 1h bar dict {datetime, open, high, low, close,
        volume}. Returns a list of events (bars emitted, session outcomes,
        rejections). Never raises on bad data — bad data is an event."""
        events = []
        stamp = str(row.get("datetime", ""))
        date, hhmm = stamp[:10], stamp[11:16]
        if self.poison is not None:
            events.append(self._reject("POISONED_FEED", stamp,
                                       f"feed poisoned: {self.poison}"))
            return events
        # schema / value validation (leg-level corruption classes)
        try:
            o, h, l, c = (float(row[k]) for k in
                          ("open", "high", "low", "close"))
            v = float(row["volume"])
            import math
            finite = all(math.isfinite(x) for x in (o, h, l, c, v))
        except Exception:
            finite, o, h, l, c, v = False, 0, 0, 0, 0, 0
        if not finite or min(o, h, l, c) <= 0 or v < 0:
            self.poison = (POISON_VALUE, stamp)
            events.append(self._reject(POISON_VALUE, stamp,
                                       "non-finite / non-positive price or "
                                       "negative volume"))
            return events
        # session / grid admission
        if not self.table.is_session(date):
            events.append(self._reject(REJ_UNKNOWN_SESSION, stamp,
                                       "date not in pinned session table"))
            return events
        # -17 CLASS PRECEDENCE (changed from -15/-16, deliberately):
        # causal bin finalization means a session is usually finalized
        # before late/duplicate/phantom stamps for it arrive, so the
        # stamp's own class must be judged before the finalized check —
        # a re-fed admitted stamp is a DUPLICATE (not LATE_BAR), and a
        # post-close stamp is the EXCLUDED phantom class (not LATE_BAR),
        # exactly as both were classified in -15/-16 before their
        # sessions finalized a day late. LATE_BAR still governs
        # never-processed on-grid stamps for a finalized date.
        key = (date, hhmm)
        if key in self.seen_stamps:
            events.append(self._reject(REJ_DUPLICATE, stamp,
                                       "stamp already processed"))
            return events
        if hhmm >= self.table.close(date):
            # post-close phantom class (e.g. 15:30 on a 13:00 close):
            # excluded by admission, exactly as the capture gates do.
            self.seen_stamps.add(key)
            if self.last_stamp is None or key > self.last_stamp:
                self.last_stamp = key
            events.append({"type": "EXCLUDED_POSTCLOSE",
                           "symbol": self.symbol, "stamp": stamp})
            # a post-close stamp seals the date: last_stamp has
            # advanced past the close, so no further admitted bar
            # can ever arrive for it — finalize causally now.
            self._emit_ready_bins(date, events, sealed=True)
            self._maybe_finalize_earlier(date, events)
            return events
        if date in self.finalized:
            events.append(self._reject(REJ_LATE_BAR, stamp,
                                       "session already finalized — "
                                       "no backfill"))
            return events
        if self.last_stamp is not None and key <= self.last_stamp:
            events.append(self._reject(REJ_OUT_OF_ORDER, stamp,
                                       "stamp not after last processed "
                                       "stamp"))
            return events
        expected = self.table.expected_starts(date)
        if hhmm not in expected:
            events.append(self._reject(
                REJ_OFF_GRID, stamp,
                "stamp outside the pinned session grid (pre-open or "
                "off-hour); legacy 06:30/10:30/14:30 stamps land here"))
            return events
        # admitted-stamp volume completeness (the G-5 class; the batch
        # admission gates evaluate volume on admitted bars only, so this
        # check runs after grid admission, never on excluded stamps)
        if v == 0 and not (o == h == l == c):
            self.poison = (POISON_VOLUME, stamp)
            events.append(self._reject(
                POISON_VOLUME, stamp,
                "price-moving zero-volume bar (capture quarantine class)"))
            return events
        # admit
        self.seen_stamps.add(key)
        self.last_stamp = key
        self.accepted.setdefault(date, {})[hhmm] = {
            "Open": o, "High": h, "Low": l, "Close": c, "Volume": v}
        # CAUSAL EMISSION (-17): finalize any bin whose full membership
        # is now strictly known, at this admission — not at the next
        # session's first bar.
        self._emit_ready_bins(date, events)
        self._maybe_finalize_earlier(date, events)
        return events

    def _build_bar(self, date, bstart, bend, members):
        """Construct one corrected 4H bar from admitted rows only.
        SessionVWAP is cumulative over the session up to this bin's
        last member — identical arithmetic to the -15/-16 batch build."""
        rows = self.accepted.get(date, {})
        expected = self.table.expected_starts(date)
        ordered = [(s, rows[s]) for s in expected if s in rows]
        bin_rows = [r for s, r in ordered if s in members]
        upto = [r for s, r in ordered if s <= members[-1]]
        pv = sum(((r["High"] + r["Low"] + r["Close"]) / 3.0)
                 * r["Volume"] for r in upto)
        vv = sum(r["Volume"] for r in upto)
        return {"symbol": self.symbol,
                "ts": pd.Timestamp(f"{date} {bstart}").tz_localize(ET),
                "decision_instant":
                    pd.Timestamp(f"{date} {bend}").tz_localize(ET),
                "Open": bin_rows[0]["Open"],
                "High": max(r["High"] for r in bin_rows),
                "Low": min(r["Low"] for r in bin_rows),
                "Close": bin_rows[-1]["Close"],
                "Volume": sum(r["Volume"] for r in bin_rows),
                "SessionVWAP": pv / vv if vv > 0 else float("nan")}

    def _emit_ready_bins(self, date, events, sealed=False):
        """Emit every bin of `date` whose membership is strictly known
        complete, in bin order, at the moment of knowledge. A bin with
        a missing member fails the session closed iff the bin's close
        has provably passed: a stamp at or beyond the bin end has been
        admitted (the missing member could now only arrive out-of-
        order and be rejected), or the date is sealed (a post-close
        stamp advanced last_stamp past the close), or the backstop
        finalizes the date. A missing member inside a still-open bin
        does NOT kill the session early — the late member is refused
        OUT_OF_ORDER if offered, exactly as in -15/-16; the bin simply
        never emits, and the failure is declared when the bin close
        passes or the backstop runs."""
        if date in self.finalized:
            return
        rows = self.accepted.get(date, {})
        bins = self.table.bins(date)
        emitted = self.emitted_bins.setdefault(date, set())
        for idx, (bstart, bend, members) in enumerate(bins):
            if idx in emitted:
                continue
            if all(m in rows for m in members):
                bar = self._build_bar(date, bstart, bend, members)
                events.append({"type": "BAR", "symbol": self.symbol,
                               "bar": bar,
                               "emitted_at": f"{date} {bend}",
                               "emission": "BIN_CLOSE_CAUSAL"})
                emitted.add(idx)
                continue
            if sealed or any(s >= bend for s in rows):
                expected = self.table.expected_starts(date)
                # `missing` = the PROVABLY absent hours at this moment:
                # every expected start the feed has already passed
                # (a later stamp is admitted, or the date is sealed).
                # Hours not yet due are not yet missing — the session
                # is dead, so they will be refused as LATE_BAR if ever
                # offered, but they are not counted here.
                if sealed:
                    missing = [s for s in expected if s not in rows]
                else:
                    horizon = max(rows)
                    missing = [s for s in expected
                               if s not in rows and s < horizon]
                self.finalized[date] = False
                events.append({"type": "SESSION_INCOMPLETE",
                               "symbol": self.symbol, "date": date,
                               "missing": missing,
                               "present": sorted(rows),
                               "emitted_bins": sorted(emitted)})
                return
            return  # earliest incomplete bin still fillable; wait
        if len(emitted) == len(bins):
            self.finalized[date] = True
            events.append({"type": "SESSION_COMPLETE",
                           "symbol": self.symbol, "date": date})

    def _maybe_finalize_earlier(self, current_date, events):
        for d in sorted(self.accepted):
            if d < current_date and d not in self.finalized:
                events.extend(self._finalize_date(d))

    def _finalize_date(self, date):
        """Backstop for a date that can no longer complete (a later
        session has started, or flush()): any bin not already emitted
        causally is a GAP — the session is incomplete, no backfill.
        (Under causal emission a complete session has already emitted
        all bins and set finalized[date]=True before this can run.)"""
        if date in self.finalized:
            return []
        rows = self.accepted.get(date, {})
        expected = self.table.expected_starts(date)
        self.finalized[date] = False
        return [{"type": "SESSION_INCOMPLETE", "symbol": self.symbol,
                 "date": date,
                 "missing": [s for s in expected if s not in rows],
                 "present": sorted(rows),
                 "emitted_bins": sorted(self.emitted_bins.get(date,
                                                              set()))}]

    def flush(self):
        events = []
        for d in sorted(self.accepted):
            if d not in self.finalized:
                events.extend(self._finalize_date(d))
        return events

    def daily_asof_rows(self):
        """Completed-session daily aggregates for the benchmark feed:
        {date: OHLCV} over FINALIZED COMPLETE sessions only."""
        out = {}
        for date, ok in self.finalized.items():
            if not ok:
                continue
            rows = [self.accepted[date][s]
                    for s in self.table.expected_starts(date)]
            out[date] = {"Open": rows[0]["Open"],
                         "High": max(r["High"] for r in rows),
                         "Low": min(r["Low"] for r in rows),
                         "Close": rows[-1]["Close"],
                         "Volume": sum(r["Volume"] for r in rows)}
        return out


# ---------------------------------------------------------- candidate machine
class CandidateMachine:
    """Streaming replica of the -13 successor candidate generation
    (gen_candidates_censored in run_study13.py, itself field-verified
    against the frozen pine_ranking.gen_candidates for closed trades).

    Steps are processed with the identical index discipline as the batch
    loop (while i < n-1; entry at Open[i+1]; exits evaluated on completed
    bars). Indicators are recomputed over the accumulated prefix frame on
    every advance — every indicator in the pinned engine is trailing
    (causal), so prefix values at index i equal full-frame values at i;
    the parity harness proves this empirically on synthetic and real
    bytes via candidate identity."""

    def __init__(self, symbol, pb):
        self.symbol = symbol
        self.pb = pb
        self.bars = []
        self.i = pb.WARMUP
        self.in_trade = False
        self.pos = None
        self.skipped_gap = 0
        self.records = {}   # (symbol, signal_idx) -> candidate record
        self.flushed = False

    def _frame(self):
        df = pd.DataFrame(
            [{k: b[k] for k in ("Open", "High", "Low", "Close", "Volume",
                                "SessionVWAP")} for b in self.bars],
            index=pd.DatetimeIndex([b["ts"] for b in self.bars]))
        return self.pb.add_pine_indicators(df)

    def on_bar(self, bar):
        self.bars.append(bar)
        return self._advance(final=False)

    def flush(self):
        events = self._advance(final=True)
        self.flushed = True
        return events

    def _advance(self, final):
        events = []
        n = len(self.bars)
        if n <= self.pb.WARMUP + 1 and not (final and self.in_trade):
            # not enough bars for any loop step (batch needs i < n-1
            # starting at WARMUP); flush censoring still applies.
            return events
        df = self._frame()
        pb = self.pb
        while self.i < n - 1:
            i = self.i
            if not self.in_trade:
                if pb.pine_buy_signal(df, i):
                    sig = df.iloc[i]
                    entry = float(df["Open"].iloc[i + 1])
                    stop0 = float(sig["Close"] - sig["atr"] * pb.SL_ATR)
                    if entry <= stop0:
                        self.skipped_gap += 1
                        events.append({"type": "SKIPPED_GAP",
                                       "symbol": self.symbol,
                                       "signal_idx": i})
                        self.i += 1
                        continue
                    self.pos = {
                        "symbol": self.symbol, "entry": entry,
                        "stop": stop0,
                        "tp1": entry + float(sig["atr"]) * pb.TP_ATR,
                        "tp_hit": False, "runner": stop0,
                        "entry_idx": i + 1, "signal_idx": i,
                        "entry_time": df.index[i + 1]}
                    self.in_trade = True
                    rec = {"symbol": self.symbol, "entry": entry,
                           "stop": stop0, "tp1": self.pos["tp1"],
                           "tp1_hit": False, "entry_time": df.index[i + 1],
                           "signal_time": df.index[i].isoformat(),
                           "signal_idx": i, "censored": False,
                           "exit": None, "exit_time": None,
                           "reason": None, "hold_bars": None}
                    self.records[(self.symbol, i)] = rec
                    events.append({"type": "CANDIDATE",
                                   "symbol": self.symbol, "signal_idx": i,
                                   "entry_time": str(df.index[i + 1]),
                                   "decision_instant":
                                       str(self.bars[i]["decision_instant"])})
                    self.i += 1
                    continue
                self.i += 1
                continue
            # in trade: evaluate completed bar i (identical to batch)
            bar = df.iloc[i]
            lo, hi, close = float(bar["Low"]), float(bar["High"]), \
                float(bar["Close"])
            pos = self.pos
            if not pos["tp_hit"] and hi >= pos["tp1"]:
                pos["tp_hit"] = True
                self.records[(self.symbol, pos["signal_idx"])]["tp1_hit"] \
                    = True
                events.append({"type": "TP1_HIT", "symbol": self.symbol,
                               "signal_idx": pos["signal_idx"]})
            if pos["tp_hit"]:
                pos["runner"] = max(pos["runner"],
                                    close - float(bar["atr"]) * pb.TRAIL_ATR)
            trend_bear = bar["e21"] < bar["e55"] and close < bar["e200"]
            reason = None
            if close < pos["runner"]:
                reason = "stop"
            elif close < bar["e55"] or trend_bear:
                reason = "ema55-bear" if trend_bear else "ema55-break"
            if reason is not None:
                exit_px = float(df["Open"].iloc[i + 1])
                exit_idx, exit_time = i + 1, df.index[i + 1]
                # QF-EQUITY43-FWD-DECISION-PARITY-REPAIR-20261023-16 —
                # MINIMAL REPAIR (observer layer only). The candidate
                # `exit` the simulators consume is NOT the raw exit-bar
                # open: the reference generator (gen_candidates_censored,
                # field-verified against frozen gen_candidates) records
                # the TP1-blended synthetic exit — 50% realized at TP1
                # when hit, the runner at the raw exit price — via the
                # identical float arithmetic below. The -15 observer
                # stored the raw open, so every tp1_hit candidate's
                # exit differed (276 of 586 on DEV bytes), cascading
                # through _outcome cash flows into 201 decision
                # mismatches. Arithmetic mirrored expression-for-
                # expression; bit-exact against the reference on all
                # 586 closed candidates (proven in the -16 package).
                risk_frac = (pos["entry"] - pos["stop"]) / pos["entry"]
                r1 = (pos["tp1"] - pos["entry"]) / pos["entry"] \
                    / risk_frac if pos["tp_hit"] else None
                r2 = (exit_px - pos["entry"]) / pos["entry"] / risk_frac
                r_blend = (0.5 * r1 + 0.5 * r2) if r1 is not None else r2
                exit_synth = pos["entry"] * (1 + r_blend * risk_frac)
                rec = self.records[(self.symbol, pos["signal_idx"])]
                rec.update({"exit": exit_synth, "exit_time": exit_time,
                            "reason": reason,
                            "hold_bars": exit_idx - pos["entry_idx"],
                            "tp1_hit": pos["tp_hit"]})
                events.append({"type": "TRADE_CLOSED",
                               "symbol": self.symbol,
                               "signal_idx": pos["signal_idx"],
                               "exit_time": str(exit_time),
                               "reason": reason})
                self.in_trade, self.pos = False, None
            self.i += 1
        if final and self.in_trade and self.pos is not None:
            pos = self.pos
            rec = self.records[(self.symbol, pos["signal_idx"])]
            rec.update({"censored": True, "exit": None, "exit_time": None,
                        "reason": "censored_terminal_open",
                        "hold_bars": None, "tp1_hit": pos["tp_hit"]})
            events.append({"type": "CENSORED", "symbol": self.symbol,
                           "signal_idx": pos["signal_idx"],
                           "entry_time": str(pos["entry_time"])})
            self.in_trade, self.pos = False, None
        return events


# ------------------------------------------------------------------ observer
class ForwardObserver:
    """Multi-symbol corrected forward observer (S1-shaped: signal-only).

    Emits NO orders, holds NO positions and computes NO P&L. Decision
    events are journaled; when `armed` and the production PAUSE sentinel
    is present, candidate decision events are journaled as WITHHELD
    instead of emitted (the gate is closed while production is paused).
    """

    def __init__(self, table, journal, pb, symbols,
                 sentinel_path=None, armed=False):
        self.table = table
        self.journal = journal
        self.pb = pb
        self.feeds = {s: SymbolFeed(s, table) for s in symbols}
        self.machines = {s: CandidateMachine(s, pb) for s in symbols}
        self.sentinel_path = sentinel_path
        self.armed = armed
        self.bars = {s: [] for s in symbols}
        self.decision_events = []

    def gate_open(self):
        if not self.armed:
            return True  # offline build mode: decisions are evidence only
        if self.sentinel_path and os.path.exists(self.sentinel_path):
            return False
        return True

    def _journal_event(self, ev, market_time):
        """Journal one feed event. -17: BAR events carry their FULL bar
        payload (the -15/-16 journal excluded it, which made journal-
        only replay impossible)."""
        payload = {k: v for k, v in ev.items()
                   if k not in ("type", "bar")}
        if ev["type"] == "BAR":
            bar = ev["bar"]
            payload["bar"] = {
                "symbol": bar["symbol"], "ts": str(bar["ts"]),
                "decision_instant": str(bar["decision_instant"]),
                "Open": bar["Open"], "High": bar["High"],
                "Low": bar["Low"], "Close": bar["Close"],
                "Volume": bar["Volume"],
                "SessionVWAP": bar["SessionVWAP"]}
        self.journal.append(ev["type"], market_time, payload)

    def ingest(self, symbol, row):
        out = []
        # -17 INPUT RECEIPT: every raw row is journaled BEFORE
        # processing, in arrival order, so the journal alone is a
        # complete, hash-chained record of everything the observer
        # consumed (accepted, excluded and rejected rows alike).
        self.journal.append("INPUT", row.get("datetime", ""),
                            {"symbol": symbol, "row": dict(row)})
        for ev in self.feeds[symbol].ingest(row):
            self._journal_event(ev, row.get("datetime", ""))
            out.append(ev)
            if ev["type"] == "BAR":
                bar = ev["bar"]
                self.bars[symbol].append(bar)
                for dev in self.machines[symbol].on_bar(bar):
                    out.append(dev)
                    self._emit_decision(dev)
        return out

    def _emit_decision(self, dev):
        if dev["type"] not in ("CANDIDATE", "TRADE_CLOSED", "CENSORED",
                               "TP1_HIT", "SKIPPED_GAP"):
            return
        if not self.gate_open():
            self.journal.append("WITHHELD_PAUSED",
                                dev.get("entry_time", ""), dev)
            return
        self.decision_events.append(dev)
        self.journal.append("DECISION", dev.get("entry_time", ""), dev)

    def flush(self):
        out = []
        for sym in sorted(self.feeds):
            for ev in self.feeds[sym].flush():
                self._journal_event(ev, ev.get("date", ""))
                out.append(ev)
                if ev["type"] == "BAR":
                    bar = ev["bar"]
                    self.bars[sym].append(bar)
                    for dev in self.machines[sym].on_bar(bar):
                        out.append(dev)
                        self._emit_decision(dev)
            for dev in self.machines[sym].flush():
                out.append(dev)
                self._emit_decision(dev)
        self.journal.append("SEALED", "", {"symbols": sorted(self.feeds)})
        return out

    # ------------------------------------------------------------ outputs
    def bars_frame(self, symbol):
        bars = self.bars[symbol]
        return pd.DataFrame(
            [{k: b[k] for k in ("Open", "High", "Low", "Close", "Volume",
                                "SessionVWAP")} for b in bars],
            index=pd.DatetimeIndex([b["ts"] for b in bars]))

    def candidates(self):
        out = []
        for sym in sorted(self.machines):
            out.extend(self.machines[sym].records.values())
        return out

    def benchmark_asof(self, bench_symbol="SPY"):
        """Strict completed-session as-of daily benchmark frame, built
        from the observer's own finalized SPY sessions (identical
        aggregation/stamping to asof_benchmark.build_daily_asof)."""
        daily = self.feeds[bench_symbol].daily_asof_rows()
        didx = (pd.DatetimeIndex([pd.Timestamp(d) for d in daily])
                + pd.Timedelta(hours=16)).tz_localize(ET) \
            .tz_convert("UTC")
        return pd.DataFrame([daily[d] for d in daily],
                            index=didx).sort_index()

    # ------------------------------------------------------ restart state
    def snapshot(self, path):
        state = {
            "contract": CONTRACT_ID,
            "bars": {s: [{"ts": str(b["ts"]),
                          "decision_instant": str(b["decision_instant"]),
                          "Open": b["Open"], "High": b["High"],
                          "Low": b["Low"], "Close": b["Close"],
                          "Volume": b["Volume"],
                          "SessionVWAP": b["SessionVWAP"]}
                         for b in bars] for s, bars in self.bars.items()},
            "feeds": {s: {"accepted": f.accepted,
                          "finalized": f.finalized,
                          "emitted_bins": {d: sorted(v) for d, v in
                                           f.emitted_bins.items()},
                          "poison": f.poison,
                          "last_stamp": f.last_stamp,
                          "seen_stamps": sorted(f.seen_stamps)}
                      for s, f in self.feeds.items()},
            "machines": {s: {"i": m.i, "in_trade": m.in_trade,
                             "pos": (None if m.pos is None else
                                     {**m.pos,
                                      "entry_time": str(m.pos["entry_time"])})
                             , "skipped_gap": m.skipped_gap,
                             "records": {f"{k[0]}|{k[1]}":
                                         {**r,
                                          "entry_time": str(r["entry_time"]),
                                          "exit_time": (None if r["exit_time"]
                                                        is None else
                                                        str(r["exit_time"]))}
                                         for k, r in m.records.items()}}
                         for s, m in self.machines.items()},
            "journal_head": self.journal.head,
            "journal_records": len(self.journal.records),
            "decision_events": self.decision_events,
        }
        with open(path, "w") as f:
            f.write(_canon(state) + "\n")
        return _sha(state)

    @classmethod
    def restore(cls, path, table, journal, pb, symbols,
                sentinel_path=None, armed=False):
        with open(path) as f:
            state = json.loads(f.read())
        if state["contract"] != CONTRACT_ID:
            raise ValueError("snapshot contract mismatch")
        if journal.head != state["journal_head"] \
                or len(journal.records) != state["journal_records"]:
            raise ValueError("journal does not match snapshot head — "
                             "refusing to restore over a divergent journal")
        obs = cls(table, journal, pb, symbols,
                  sentinel_path=sentinel_path, armed=armed)
        def _ts(x):
            t = pd.Timestamp(x)
            return t.tz_convert(ET) if t.tz is not None else t
        for s, bars in state["bars"].items():
            obs.bars[s] = [{"symbol": s,
                            "ts": _ts(b["ts"]),
                            "decision_instant":
                                _ts(b["decision_instant"]),
                            "Open": b["Open"], "High": b["High"],
                            "Low": b["Low"], "Close": b["Close"],
                            "Volume": b["Volume"],
                            "SessionVWAP": b["SessionVWAP"]}
                           for b in bars]
        for s, fs in state["feeds"].items():
            f = obs.feeds[s]
            f.accepted = {d: dict(rows) for d, rows in
                          fs["accepted"].items()}
            f.finalized = dict(fs["finalized"])
            f.emitted_bins = {d: set(v) for d, v in
                              fs.get("emitted_bins", {}).items()}
            f.poison = tuple(fs["poison"]) if fs["poison"] else None
            f.last_stamp = tuple(fs["last_stamp"]) if fs["last_stamp"] \
                else None
            f.seen_stamps = {tuple(x) for x in fs["seen_stamps"]}
        for s, ms in state["machines"].items():
            m = obs.machines[s]
            m.bars = list(obs.bars[s])
            m.i = ms["i"]
            m.in_trade = ms["in_trade"]
            m.skipped_gap = ms["skipped_gap"]
            if ms["pos"] is not None:
                m.pos = {**ms["pos"],
                         "entry_time": _ts(ms["pos"]["entry_time"])}
            for kk, r in ms["records"].items():
                sym, idx = kk.rsplit("|", 1)
                m.records[(sym, int(idx))] = {
                    **r, "entry_time": _ts(r["entry_time"]),
                    "exit_time": (None if r["exit_time"] is None
                                  else _ts(r["exit_time"]))}
        obs.decision_events = state["decision_events"]
        return obs


# ------------------------------------------------------------- replay (-17)
def replay_journal(journal_path, anchor_path, table, pb, symbols,
                   out_journal_path, out_anchor_path,
                   sentinel_path=None, armed=False):
    """Rebuild a complete run from its journal ALONE (-17 provenance
    proof). The journal's INPUT records are the immutable input
    receipts; SEALED records mark the points where the original run
    called flush(). Replaying the INPUT payloads in journal order
    (with flush() at each SEALED) through a fresh observer must
    reproduce the original journal BYTE-IDENTICALLY — every BAR
    payload, rejection, decision and chain hash included. Returns
    (ok, info); ok is True only on byte identity after the source
    journal itself verifies against its external anchor."""
    ok, info = Journal.verify(journal_path, anchor_path)
    if not ok:
        return False, {"source_journal_verify": info}
    with open(journal_path) as f:
        recs = [json.loads(ln) for ln in f.read().splitlines()]
    j2 = Journal(out_journal_path, out_anchor_path)
    obs = ForwardObserver(table, j2, pb, symbols,
                          sentinel_path=sentinel_path, armed=armed)
    n_inputs = 0
    for rec in recs:
        if rec["type"] == "INPUT":
            obs.ingest(rec["payload"]["symbol"], rec["payload"]["row"])
            n_inputs += 1
        elif rec["type"] == "SEALED":
            obs.flush()
    j2.close()
    with open(journal_path, "rb") as f:
        orig_bytes = f.read()
    with open(out_journal_path, "rb") as f:
        replay_bytes = f.read()
    same = orig_bytes == replay_bytes
    return same, {"inputs_replayed": n_inputs,
                  "records_original": len(recs),
                  "records_replay": len(j2.records),
                  "byte_identical": same,
                  "journal_sha256_original":
                      hashlib.sha256(orig_bytes).hexdigest(),
                  "journal_sha256_replay":
                      hashlib.sha256(replay_bytes).hexdigest()}
